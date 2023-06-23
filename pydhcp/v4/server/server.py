"""
PyServe Session DHCPv4 Implementation
"""
from abc import ABC, abstractmethod
from ipaddress import IPv4Address
from logging import Logger, getLogger
from typing import Callable, List, Optional

from pyserve import Address, UdpWriter
from pyserve import Session as BaseSession
from pyderive import dataclass, field

from ..enum import MessageType, OpCode, OptionCode
from ..message import IpType, Message
from ..options import *
from ...enum import StatusCode
from ...exceptions import DhcpError, NotAllowed, UnknownQueryType

#** Variables **#
__all__ = ['HandlerFunc', 'Session', 'SimpleSession']

#: dhcp response port
PORT = 68

#: broadcast request for responding to messages
BROADCAST = IPv4Address('255.255.255.255')

#: required opcodes to preserve even when not requested
REQUIRED = {OptionCode.DHCPMessageType, }

#: function definition for session processing callback
HandlerFunc = Callable[[Message, Message], None]

#: logger generation function
getBackLogger = lambda: getLogger('pydhcp')

#** Functions **#

def is_zero(host: IpType) -> bool:
    """check if host-ip is zeroed"""
    return len(IPv4Address(host).packed.strip(b'\x00')) == 0

def find_host(*ips: IpType) -> IPv4Address:
    """search through available ips to find first non-zero available"""
    for ip in (IPv4Address(ip) for ip in ips):
        if not is_zero(ip):
            return ip
    raise RuntimeError(f'No NonZero IPs: {ips!r}')

def mac_address(hwaddr: bytes) -> str:
    """translate hardware address to mac"""
    return ':'.join(f'{c:02x}' for c in hwaddr)

def validate_options(req: Message, res: Message):
    """validate and filter options based on requested operation-codes"""
    options   = OptionList()
    requested = set(req.requested_options())
    for option in res.options:
        if option.opcode in requested or option.opcode in REQUIRED:
            continue
        options.append(option)
    res.options = options

#** Classes **#

@dataclass
class Session(BaseSession, ABC):
    logger: Logger = field(default_factory=getBackLogger)

    ## Overrides

    @abstractmethod
    def process_discover(self, req: Message) -> Optional[Message]:
        raise NotImplementedError 

    @abstractmethod
    def process_request(self, req: Message) -> Optional[Message]:
        raise NotImplementedError 

    @abstractmethod
    def process_decline(self, req: Message) -> Optional[Message]:
        raise NotImplementedError 

    @abstractmethod
    def process_release(self, req: Message) -> Optional[Message]:
        raise NotImplementedError 

    @abstractmethod
    def process_inform(self, req: Message) -> Optional[Message]:
        raise NotImplementedError

    @abstractmethod
    def process_unknown(self, req: Message) -> Optional[Message]:
        raise NotImplementedError

    def default_response(self, req: Message) -> Message:
        """Generate Default DHCP Response"""
        return Message(
            op=OpCode.BootReply,
            id=req.id,
            client_hw=req.client_hw,
            options=OptionList(),
        )
 
    def send(self, request: Message, response: Message):
        """send completed response message"""
        hosts = (
            request.gateway_addr,
            request.client_addr,
            IPv4Address(self.addr.host),
            BROADCAST,
        )
        # sort options by opcode
        response.options.sort()
        # encode and send response
        data = response.encode()
        for ipv4 in hosts:
            if is_zero(ipv4):
                continue
            host = str(ipv4)
            info = f'{self.addr_str} | sent {len(data)} bytes to {host}:{PORT}'
            self.logger.debug(info)
            self.writer.write(data, addr=(host, PORT))

    ## Session Impl

    def connection_made(self, addr: Address, writer: UdpWriter):
        """handle session initialization on connection-made"""
        self.addr      = addr
        self.writer    = writer
        self.addr_str  = '%s:%d' % self.addr

    def data_recieved(self, data: bytes):
        """recieve DHCPv4 request and generate response"""
        self.logger.debug(f'{self.addr_str} | recieved {len(data)} bytes')
        # parse initial request message
        request      = Message.decode(data)
        message_type = request.message_type()
        if message_type is None:
            self.logger.warning(f'{self.addr_str} | no message-type specified')
        # send to relevant handler
        response: Optional[Message] = None
        try:
            if message_type == MessageType.Discover:
                response = self.process_discover(request)
            elif message_type == MessageType.Request:
                response = self.process_request(request)
            elif message_type == MessageType.Decline:
                response = self.process_decline(request)
            elif message_type == MessageType.Release:
                response = self.process_release(request)
            elif message_type == MessageType.Inform:
                response = self.process_inform(request)
            else:
                response = self.process_unknown(request)
        except DhcpError as e:
            nak      = OptMessageType(MessageType.Nak)
            status   = OptStatusCode(e.code, str(e).encode())
            response = response or self.default_response(request)
            response.options.extend([nak, status])
        except Exception as e:
            nak      = OptMessageType(MessageType.Nak)
            status   = OptStatusCode(StatusCode.UnspecFail, str(e).encode())
            response = response or self.default_response(request)
            response.options.extend([nak, status])
            raise e
        finally:
            if response is not None:
                self.send(request, response)
            else:
                self.logger.error(f'{self.addr_str} | No Response Given.')
                self.writer.close()

    def connection_lost(self, err: Optional[Exception]):
        """debug log connection lost"""
        msg = f'{self.addr_str} | connection-lost err={err}'
        log = self.logger.warning if err is not None else self.logger.debug
        log(msg)

@dataclass(slots=True)
class SimpleSession(Session):
    """Simplified DHCP Server Implementation"""
    handlers:  List[HandlerFunc] = field(default_factory=list)
    releasers: List[HandlerFunc] = field(default_factory=list)
 
    def __post_init__(self):
        if not self.handlers:
            raise ValueError('SimpleSession Handlers Empty!')

    def process_discover(self, req: Message) -> Optional[Message]:
        """process incoming discover request"""
        msg = OptMessageType(MessageType.Offer)
        res = self.default_response(req)
        for func in self.handlers:
            func(req, res)
        validate_options(req, res)
        res.options.setdefault(msg.opcode, msg)
        # ensure your-ip is set during exchange
        if not res.your_addr:
            raise RuntimeError(f'Handlers Failed to Assign Client-IP')
        return res

    def process_request(self, req: Message) -> Optional[Message]:
        """process incoming dhcp request"""
        msg = OptMessageType(MessageType.Ack)
        res = self.default_response(req)
        for handler in self.handlers:
            handler(req, res)
        validate_options(req, res)
        req.options.setdefault(msg.opcode, msg)
        # ensure your-ip is set during exchange
        if not res.your_addr:
            raise RuntimeError(f'Handlers Failed to Assign Client-IP')
        # ensure assignment matches request
        netmask  = res.options.get(OptSubnetMask.opcode)
        netmask  = netmask.value if netmask else None
        req_addr = req.requested_address()
        req_cast = req.broadcast_address()
        conflict = req_addr and req_addr != res.your_addr
        conflict = conflict or req_cast and req_cast != netmask
        if conflict:
            self.logger.warning(f'{self.addr_str} | REQUEST NAK {req_addr!r}')
            nak = OptMessageType(MessageType.Nak)
            res.options.set(nak.opcode, nak)
        return res

    def process_decline(self, req: Message) -> Optional[Message]:
        """process incoming decline response"""
        mac = mac_address(req.client_hw)
        res = self.default_response(req)
        msg = OptMessageType(MessageType.Nak)
        self.logger.info(f'{self.addr_str} | DECLINE {mac} {req.client_addr}')
        for func in self.handlers:
            func(req, res)
        validate_options(req, res)
        res.options.setdefault(msg.opcode, msg)
        return res

    def process_release(self, req: Message) -> Optional[Message]:
        """process incoming release request"""
        mac = mac_address(req.client_hw)
        res = self.default_response(req)
        msg = OptMessageType(MessageType.Ack)
        self.logger.info(f'{self.addr_str} | RELEASE {mac} {req.client_addr}')
        for func in self.release_funcs:
            func(req, res)
        validate_options(req, res)
        res.options.setdefault(msg.opcode, msg)
        return res

    def process_inform(self, _: Message) -> Optional[Message]:
        """process incoming inform request"""
        raise NotAllowed('Inform not Allowed')
 
    def process_unknown(self, _: Message) -> Optional[Message]:
        raise UnknownQueryType('Unsupported MessageType')
