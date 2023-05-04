"""
PyServe Session DHCPv4 Implementation
"""
from abc import ABC, abstractmethod
from ipaddress import IPv4Address
from logging import Logger, getLogger
from dataclasses import dataclass, field
from typing import Optional

from pyserve import Address, Writer
from pyserve import Session as BaseSession

from .backend import Backend
from ..enum import MessageType, OpCode
from ..message import Message
from ..options import *
from ...enum import StatusCode
from ...exceptions import DhcpError, NotAllowed, NotSupported, UnknownQueryType

#** Variables **#
__all__ = ['Session', 'SimpleSession']

#: broadcast request for responding to messages
BROADCAST = '255.255.255.255'

#** Functions **#

def mac_address(hwaddr: bytes) -> str:
    """translate hardware address to mac"""
    return ':'.join(f'{c:02x}' for c in hwaddr)

#** Classes **#

@dataclass
class Session(BaseSession, ABC):
    backend:   Backend
    logger:    Logger = field(default_factory=lambda: getLogger('pydhcp'))
    server_id: Optional[IPv4Address] = None

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

    ## Session Impl

    def connection_made(self, addr: Address, writer: Writer):
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
            if response is None:
                self.logger.error(f'{self.addr_str} | No Response Given.')
                self.writer.close()
            else:
                # apply server-identifier when given
                if self.server_id:
                    response.options.append(OptServerId(self.server_id))
                # encode and send response
                data = response.encode()
                self.logger.debug(f'{self.addr_str} | sent {len(data)} bytes')
                self.writer.write(data)

    def connection_lost(self, err: Optional[Exception]):
        """debug log connection lost"""
        self.logger.debug(f'{self.addr_str} | connection-lost err={err}')

@dataclass
class SimpleSession(Session):
    backend: Backend
    logger:  Logger = field(default_factory=lambda: getLogger('pydhcp'))

    def process_discover(self, req: Message) -> Optional[Message]:
        """process discover according to backend"""
        # retrieve and log assignment
        mac    = req.client_hw.hex()
        answer = self.backend.get_assignment(req.client_hw)
        assign = answer.assign
        self.logger.info(f'{self.addr_str} | DISCOVER {mac} {answer}')
        # offer assignment on discover 
        res = self.default_response(req)
        res.your_addr = assign.your_addr
        if self.server_id is not None:
            res.server_addr = self.server_id
        res.options.extend([
            OptMessageType(MessageType.Offer),
            OptDNS(assign.dns),
            OptRouter(assign.gateway),
            OptSubnetMask(assign.netmask),
            OptIPLeaseTime(assign.lease_seconds),
        ])
        return res

    def process_request(self, req: Message) -> Optional[Message]:
        """process request according to backend"""
        # retrieve and log assignment
        mac    = req.client_hw.hex()
        answer = self.backend.get_assignment(req.client_hw)
        assign = answer.assign
        self.logger.info(f'{self.addr_str} | REQUEST {mac} {answer}')
        # build list of response options based on request
        reqops  = set(req.requested_options())
        options = [opt for opt in (
            OptDNS(assign.dns),
            OptRouter(assign.gateway),
            OptSubnetMask(assign.netmask),
            OptBroadcast(assign.broadcast),
        ) if reqops and opt.opcode in reqops]
        # raise error if cannot satisfy and options
        if not options:
            raise NotSupported('No Requested Options Supported')
        # build standard response
        res = self.default_response(req)
        res.your_addr = assign.your_addr
        res.options.extend([
            OptMessageType(MessageType.Ack),
            OptIPLeaseTime(assign.lease_seconds),
            *options,
        ])
        # check if request conflicts with server assignment
        req_addr = req.requested_address()
        req_cast = req.broadcast_address()
        conflict = req_addr and req_addr != assign.your_addr
        conflict = conflict or req_cast and req_cast != assign.netmask
        if conflict:
            self.logger.warning(f'{self.addr_str} | REQUEST NAK {req_addr!r}')
            nak = OptMessageType(MessageType.Nak)
            res.options.set(nak.opcode, nak)
        return res

    def process_decline(self, req: Message) -> Optional[Message]:
        """process decline message according to backend"""
        mac    = mac_address(req.client_hw)
        assign = self.backend.get_assignment(req.client_hw).assign
        self.logger.info(f'{self.addr_str} | DECLINE {mac} {assign.client}')
        self.backend.del_assignment(req.client_hw)
        res = self.default_response(req)
        res.options.append(OptMessageType(MessageType.Nak))
        return res

    def process_release(self, req: Message) -> Optional[Message]:
        """process release message according to backend"""
        mac    = mac_address(req.client_hw)
        assign = self.backend.get_assignment(req.client_hw).assign
        self.logger.info(f'{self.addr_str} | RELEASE {mac} {assign.client}')
        self.backend.del_assignment(req.client_hw)
        res = self.default_response(req)
        res.options.append(OptMessageType(MessageType.Ack))
        return res

    def process_inform(self, _: Message) -> Optional[Message]:
        """process inform message according to backend"""
        raise NotAllowed('Inform not Allowed')
 
    def process_unknown(self, _: Message) -> Optional[Message]:
        raise UnknownQueryType('Unsupported MessageType')
