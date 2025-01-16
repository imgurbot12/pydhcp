"""
Simple and Extensible DHCP Server Implementation
"""
from ipaddress import IPv4Address
from logging import Logger, getLogger
from typing import Optional, cast

from pyderive import dataclass, field
from pyserve import Address, Session as BaseSession, UdpWriter, Writer

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

def assign_zero(original: IPv4Address, new: IPv4Address) -> IPv4Address:
    """
    re-assign ip-address if original is zerod ip-address

    :param original: original ip-address
    :param new:      new ip-address to assign
    :return:         non-zeroed ip-address
    """
    return new if original == ZeroIp else original

#** Classes **#

@dataclass
class Server(BaseSession):
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

    def process_discover(self, request: Message) -> Optional[Message]:
        """
        Process DHCP DISCOVER Message
        """
        answer = self.backend.discover(self.client, request)
        if answer is None:
            return
        response = answer.message
        response.server_addr = assign_zero(response.server_addr, self.server_id)
        response.options.insert(0, DHCPMessageType(MessageType.Offer))
        response.options.insert(1, ServerIdentifier(self.server_id))
        return response

    def process_request(self, request: Message) -> Optional[Message]:
        """
        Process DHCP REQUEST Message
        """
        answer = self.backend.request(self.client, request)
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
        return response

    def process_decline(self, request: Message) -> Optional[Message]:
        """
        Process DHCP DECLINE Message
        """
        answer   = self.backend.decline(self.client, request)
        response = answer.message if answer else request.reply()
        response.server_addr = assign_zero(response.server_addr, self.server_id)
        response.options.setdefault(DHCPMessageType(MessageType.Nak), 0)
        response.options.setdefault(ServerIdentifier(self.server_id), 1)
        return response

    def process_release(self, request: Message) -> Optional[Message]:
        """
        Process DHCP RELEASE Message
        """
        answer   = self.backend.release(self.client, request)
        response = answer.message if answer else request.reply()
        response.server_addr = assign_zero(response.server_addr, self.server_id)
        response.options.setdefault(DHCPMessageType(MessageType.Ack), 0)
        response.options.setdefault(ServerIdentifier(self.server_id), 1)
        return response

    def process_inform(self, request: Message) -> Optional[Message]:
        """
        Process DHCP INFORM Message
        """
        raise NotAllowed('Inform Not Allowed')

    def process_unknown(self, request: Message) -> Optional[Message]:
        """
        Process Unknown/Invalid DHCP Messages
        """
        raise UnknownQueryType(f'Unknown Message: {request.message_type()!r}')

    ### Standard Handlers

    def connection_made(self, addr: Address, writer: Writer):
        """
        handle session initialization on connection-made
        """
        self.client:   Address   = addr
        self.writer:   UdpWriter = cast(UdpWriter, writer)
        self.addr_str: str       = '%s:%d' % self.client
        self.logger.debug(f'{self.addr_str} | connection-made')

    def _send(self, request: Message, response: Optional[Message]):
        """
        broadcast dhcp response packet to the relevant ips
        """
        if not response:
            self.logger.error(f'{self.addr_str} | no response given.')
            self.writer.close()
            return
        data = response.pack().rjust(300, b'\x00')
        host = assign_zero(request.client_addr, request.gateway_addr)
        host = assign_zero(host, IPv4Address(self.client.host))
        host = assign_zero(host, self.broadcast)
        host = str(host)
        self.logger.debug(
            f'{self.addr_str} | sent {len(data)} bytes to {host}:{PORT}')
        self.writer.write(data, addr=(host, PORT))

    def data_recieved(self, data: bytes):
        """
        parse raw packet-data and process request
        """
        self.logger.debug(f'{self.addr_str} | recieved {len(data)} bytes')
        request      = Message.unpack(data)
        message_type = request.message_type()
        if message_type is None:
            return
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
            response = response or request.reply()
            response.options.setdefault(DHCPMessageType(MessageType.Nak), 0)
            response.options.setdefault(DHCPStatusCode(e.code, str(e).encode()))
        except Exception as e:
            code     = StatusCode.UnspecFail
            response = response or request.reply()
            response.options.setdefault(DHCPMessageType(MessageType.Nak))
            response.options.setdefault(DHCPStatusCode(code, str(e).encode()))
            raise e
        finally:
            self._send(request, response)

    def connection_lost(self, err: Optional[Exception]):
        """
        debug log connection lost
        """
        self.logger.debug(f'{self.addr_str} | connection-lost err={err}')
