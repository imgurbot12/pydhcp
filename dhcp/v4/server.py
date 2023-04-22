"""
PyServe Session DHCPv4 Implementation
"""
from abc import ABC, abstractmethod
from logging import Logger, getLogger
from dataclasses import dataclass, field
from typing import Optional

from pyserve import Address, Writer
from pyserve import Session as BaseSession

from .enum import MessageType, OpCode
from .message import Message
from .options import OptionList, OptStatusCode
from ..enum import StatusCode
from ..exceptions import DhcpError, MalformedQuery

#** Variables **#
__all__ = ['Session']

#** Classes **#

@dataclass
class Session(BaseSession, ABC):
    logger: Logger = field(default_factory=lambda: getLogger('pydhcp'))

    ## Overrides

    @abstractmethod
    def process_discover(self, req: Message) -> Optional[Message]:
        pass

    @abstractmethod
    def process_request(self, req: Message) -> Optional[Message]:
        pass

    @abstractmethod
    def process_decline(self, req: Message) -> Optional[Message]:
        pass

    @abstractmethod
    def process_release(self, req: Message) -> Optional[Message]:
        pass

    @abstractmethod
    def process_inform(self, req: Message) -> Optional[Message]:
        pass
 
    @abstractmethod
    def process_unknown(self, req: Message) -> Optional[Message]:
        raise MalformedQuery('Unsupported MessageType')

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
        self.addr     = addr
        self.writer   = writer
        self.addr_str = '%s:%d' % self.addr

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
            option   = OptStatusCode(e.code, str(e).encode())
            response = response or self.default_response(request)
            response.options.append(option)
        except Exception as e:
            option   = OptStatusCode(StatusCode.UnspecFail, str(e).encode())
            response = response or self.default_response(request)
            response.options.append(option)
            raise e
        finally:
            if response is not None:
                data = response.encode()
                self.logger.debug(f'{self.addr_str} | sent {len(data)} bytes')
                self.writer.write(data)

    def connection_lost(self, err: Optional[Exception]):
        """debug log connection lost"""
        self.logger.debug(f'{self.addr_str} | connection-lost err={err}')
