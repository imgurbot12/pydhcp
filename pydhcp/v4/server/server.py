"""
Simple and Extensible DHCP Server Implementation
"""
from ipaddress import IPv4Address
from logging import Logger, getLogger
from typing import Optional, cast

from pyderive import dataclass, field
from pyserve import Address, AsyncSession, UdpWriter, Writer

from ..  import Message, MessageType, ZeroIp
from ..  import DhcpError, NotAllowed, UnknownQueryType
from ..  import DHCPMessageType, DHCPStatusCode, ServerIdentifier
from ... import StatusCode

from .backend import Backend

#** Variables **#
__all__ = ['Server']

#: dhcp response port
PORT = 68

#: broadcast request for responding to messages
BROADCAST = IPv4Address('255.255.255.255')

#** Function **#

def mtype(response: Message) -> str:
    """
    retrieve message type string from message object

    :param response: response message object
    :return:         response message type as string
    """
    mtype = response.message_type()
    return mtype.name.upper() if mtype else 'UNKNOWN'

def assign_zero(original: IPv4Address, new: IPv4Address) -> IPv4Address:
    """
    Reassign ip-address if original is zerod ip-address

    :param original: original ip-address
    :param new:      new ip-address to assign
    :return:         non-zeroed ip-address
    """
    return new if original == ZeroIp else original

#** Classes **#

@dataclass
class Server(AsyncSession):
    """
    Extendable Implementation of DHCP Server Session Manager for PyServe
    """
    backend:   Backend
    server_id: IPv4Address
    broadcast: IPv4Address = field(default_factory=lambda: BROADCAST)
    logger:    Logger      = field(default_factory=lambda: getLogger('pydhcp'))

    def __post_init__(self):
        setattr(self.backend, 'logger', self.logger)

    ### DHCP Handlers

    async def process_discover(self, request: Message) -> Optional[Message]:
        """
        Process DHCP DISCOVER Message
        """
        self.logger.debug(f'{self.addr_str} < DISCOVER'
            f' mac={request.client_hw.hex()} ip={request.requested_address()}')
        answer = await self.backend.discover(self.client, request)
        if answer is None:
            return
        response = answer.message
        response.server_addr = assign_zero(response.server_addr, self.server_id)
        response.options.insert(0, DHCPMessageType(MessageType.Offer))
        response.options.insert(1, ServerIdentifier(self.server_id))
        self.logger.debug(self.addr_str +
            f' > {mtype(response)} mac={request.client_hw.hex()}')
        return response

    async def process_request(self, request: Message) -> Optional[Message]:
        """
        Process DHCP REQUEST Message
        """
        self.logger.debug(f'{self.addr_str} < REQUEST'
            f' mac={request.client_hw.hex()} ip={request.requested_address()}')
        answer = await self.backend.request(self.client, request)
        if answer is None:
            return
        # ensure required response components are present
        response = answer.message
        response.server_addr = assign_zero(response.server_addr, self.server_id)
        response.options.setdefault(DHCPMessageType(MessageType.Ack), 0)
        response.options.setdefault(ServerIdentifier(self.server_id), 1)
        # ensure assignment matches request
        netmask  = request.subnet_mask()
        req_addr = request.requested_address()
        req_cast = request.broadcast_address()
        if (req_addr and req_addr != response.your_addr) \
            or (req_cast and req_cast != netmask):
            response.options.insert(0, DHCPMessageType(MessageType.Nak))
        self.logger.debug(self.addr_str +
            f' > {mtype(response)} mac={request.client_hw.hex()}')
        return response

    async def process_decline(self, request: Message) -> Optional[Message]:
        """
        Process DHCP DECLINE Message
        """
        self.logger.debug(f'{self.addr_str} < DECLINE'
            f' mac={request.client_hw.hex()} ip={request.requested_address()}')
        answer   = await self.backend.decline(self.client, request)
        response = answer.message if answer else request.reply()
        response.server_addr = assign_zero(response.server_addr, self.server_id)
        response.options.setdefault(DHCPMessageType(MessageType.Nak), 0)
        response.options.setdefault(ServerIdentifier(self.server_id), 1)
        self.logger.debug(self.addr_str +
            f' > {mtype(response)} mac={request.client_hw.hex()}')
        return response

    async def process_release(self, request: Message) -> Optional[Message]:
        """
        Process DHCP RELEASE Message
        """
        self.logger.debug(f'{self.addr_str} < RELEASE'
            f' mac={request.client_hw.hex()} ip={request.requested_address()}')
        answer   = await self.backend.release(self.client, request)
        response = answer.message if answer else request.reply()
        response.server_addr = assign_zero(response.server_addr, self.server_id)
        response.options.setdefault(DHCPMessageType(MessageType.Ack), 0)
        response.options.setdefault(ServerIdentifier(self.server_id), 1)
        self.logger.debug(self.addr_str +
            f' > {mtype(response)} mac={request.client_hw.hex()}')
        return response

    async def process_inform(self, request: Message) -> Optional[Message]:
        """
        Process DHCP INFORM Message
        """
        raise NotAllowed('Inform Not Allowed')

    async def process_unknown(self, request: Message) -> Optional[Message]:
        """
        Process Unknown/Invalid DHCP Messages
        """
        raise UnknownQueryType(f'Unknown Message: {request.message_type()!r}')

    ### Standard Handlers

    async def connection_made(self, addr: Address, writer: Writer):
        """
        Handle session initialization on connection-made
        """
        self.client:   Address   = addr
        self.writer:   UdpWriter = cast(UdpWriter, writer)
        self.addr_str: str       = '%s:%d' % self.client
        self.logger.debug(f'{self.addr_str} | connection-made')

    def _send(self, request: Message, response: Optional[Message]):
        """
        Broadcast DHCP response packet to the relevant ips
        """
        if not response:
            self.logger.error(f'{self.addr_str} | no response given.')
            self.writer.close()
            return
        # NOTE: BOOTP official RFC says packets must be a minimum size
        # of 300 octets to be considered valid and not potetially dropped.
        # so historically we've padded the packed response with zero bytes
        # to match the minimum, however that seemingly breaks DHCP for
        # some networks. Instead we switch to a warning log
        data = response.pack() # .rjust(300, b'\x00')
        if len(data) < 300:
            self.logger.warning(
                f'{self.addr_str} | response less than 300 octets {len(data)}')
        host = assign_zero(request.client_addr, request.gateway_addr)
        host = assign_zero(host, IPv4Address(self.client.host))
        host = assign_zero(host, self.broadcast)
        host = str(host)
        self.logger.debug(
            f'{self.addr_str} > sent {len(data)} bytes to {host}:{PORT}')
        self.writer.write(data, addr=(host, PORT))

    async def data_received(self, data: bytes):
        """
        Parse raw packet-data and process request
        """
        self.logger.debug(f'{self.addr_str} < recieved {len(data)} bytes')
        request      = Message.unpack(data)
        message_type = request.message_type()
        if message_type is None:
            return
        response: Optional[Message] = None
        try:
            if message_type == MessageType.Discover:
                response = await self.process_discover(request)
            elif message_type == MessageType.Request:
                response = await self.process_request(request)
            elif message_type == MessageType.Decline:
                response = await self.process_decline(request)
            elif message_type == MessageType.Release:
                response = await self.process_release(request)
            elif message_type == MessageType.Inform:
                response = await self.process_inform(request)
            else:
                response = await self.process_unknown(request)
        except DhcpError as e:
            response = response or request.reply()
            response.options.setdefault(DHCPMessageType(MessageType.Nak), 0)
            response.options.setdefault(DHCPStatusCode(e.code, str(e).encode()))
        except Exception as e:
            code     = StatusCode.UnspecFail
            response = response or request.reply()
            response.options.setdefault(DHCPMessageType(MessageType.Nak))
            response.options.setdefault(DHCPStatusCode(code, str(e).encode()))
            self.logger.exception(f'{self.addr_str} | captured exception')
        finally:
            self._send(request, response)

    async def connection_lost(self, err: Optional[Exception]):
        """
        Debug log connection lost
        """
        self.logger.debug(f'{self.addr_str} | connection-lost err={err}')
