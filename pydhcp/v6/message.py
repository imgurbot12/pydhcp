"""
DHCPv6 Message Implementation
"""
from ipaddress import IPv6Address
from typing import Union
from typing_extensions import Annotated, Self

from pystructs import *
from pyderive import dataclass, field, asdict

from .enum import MessageType
from .options import OptionList, read_option

#** Variables **#
__all__ = ['Message']

#: codec type to support MessageType
MessageInt = Annotated[MessageType, Wrap[U8, MessageType]]

#** Functions **#

def read_options(ctx: Context, raw: bytes) -> OptionList:
    """read options from raw-bytes and return options-list"""
    options = OptionList()
    while ctx.index < len(raw):
        option = read_option(ctx, raw)
        options.append(option)
    return options

def write_options(ctx: Context, data: bytearray, options: OptionList):
    """serialize options into bytearray"""
    for option in options:
        data += option.encode(ctx)

#** Classes **#

class MsgHeader(Struct):
    op: MessageInt
    id: U24

class RelayForwardHeader(Struct):
    op:        MessageInt
    hops:      U16
    link_addr: IPv6
    peer_addr: IPv6

class RelayReplyHeader(Struct):
    op:        MessageInt
    link_addr: IPv6
    peer_addr: IPv6

@dataclass(slots=True, repr=False)
class Message:
    op:      MessageType
    id:      int
    options: OptionList = field(default_factory=OptionList)
 
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return f'{cname}(op={self.op.name}, id=0x{self.id:02x})'

    def encode(self) -> bytes:
        """
        Encode DHCPv6 client/server message into bytes
        """
        ctx   = Context()
        data  = bytearray()
        data += MsgHeader(self.op, self.id).encode(ctx)
        write_options(ctx, data, self.options)
        return bytes(data)

    @classmethod
    def decode(cls, raw: bytes) -> Self:
        """
        Decode DHCPv6 client/server message from bytes
        """
        ctx     = Context()
        header  = MsgHeader.decode(ctx, raw)
        options = read_options(ctx, raw)
        return cls(header.op, header.id, options)

@dataclass(slots=True, repr=False)
class RelayReplyMessage:
    op:        MessageType
    link_addr: Ipv6Type
    peer_addr: Ipv6Type
    options:   OptionList 

    def __repr__(self) -> str:
        cname  = self.__class__.__name__
        values = ' '.join(f'{k}={v}' for k, v in {
            'op':  self.op.name,
            'hops':getattr(self, 'hops', None), 
            'link': self.link_addr, 
            'peer': self.peer_addr
        }.items() if v is not None)
        return f'{cname}({values})'

    def encode(self) -> bytes:
        """
        Encode DHCPv6 RelayReply message into bytes
        """
        fields = asdict(self)
        fields.pop('options', None)
        # serialize content
        ctx   = Context()
        data  = bytearray()
        data += RelayReplyHeader(**fields).encode(ctx)
        write_options(ctx, data, self.options)
        return bytes(data)
 
    @classmethod
    def decode(cls, raw: bytes) -> Self:
        """
        Decode DHCPv6 RelayReply message from bytes
        """
        ctx     = Context()
        header  = RelayReplyHeader.decode(ctx, raw)
        fields  = asdict(header) #type: ignore
        options = read_options(ctx, raw)
        return cls(options=options, **fields)

@dataclass(slots=True, repr=False)
class RelayForwardMessage(RelayReplyMessage):
    op:        MessageType
    hops:      int
    link_addr: Ipv6Type
    peer_addr: Ipv6Type
    options:   OptionList

    def encode(self) -> bytes:
        """
        Encode DHCPv6 RelayForward message into bytes
        """
        ctx   = Context()
        data  = bytearray()
        data += RelayForwardHeader(self.op, 
            self.hops, self.link_addr, self.peer_addr).encode(ctx)
        write_options(ctx, data, self.options)
        return bytes(data)

    @classmethod
    def decode(cls, raw: bytes) -> Self:
        """
        Decode DHCPv6 RelayForward message from bytes
        """
        ctx     = Context()
        header  = RelayForwardHeader.decode(ctx, raw)
        options = read_options(ctx, raw)
        return cls(
            op=header.op, 
            hops=header.hops, 
            link_addr=header.link_addr, 
            peer_addr=header.peer_addr, 
            options=options
        )
