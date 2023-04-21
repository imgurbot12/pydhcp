"""
DHCPv6 Message Implementation
"""
from dataclasses import dataclass, field, asdict
from ipaddress import IPv6Address
from typing import Union
from typing_extensions import Self

from pystructs import Context, Int, Int16, Ipv6, struct

from .enum import MessageType
from .options import OptionList, read_option

#** Variables **#
__all__ = ['Message']

#: codec type to support MessageType
MessageInt = Int[8, MessageType, 'MessageType']

#: valid types supported for ipv6-address
IpType = Union[str, bytes, IPv6Address]

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

@struct
class MsgHeader:
    op: MessageInt
    id: Int[24]

@struct
class RelayForwardHeader:
    op:        MessageInt
    hops:      Int16
    link_addr: Ipv6
    peer_addr: Ipv6

@struct
class RelayReplyHeader:
    op:        MessageInt
    link_addr: Ipv6
    peer_addr: Ipv6 

@dataclass(repr=False)
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


@dataclass(repr=False)
class RelayReplyMessage:
    op:        MessageType
    link_addr: IpType
    peer_addr: IpType
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
        data += RelayForwardHeader(**fields).encode(ctx)
        write_options(ctx, data, self.options)
        return bytes(data)
    
    @classmethod
    def decode(cls, raw: bytes) -> Self:
        """
        Decode DHCPv6 RelayReply message from bytes
        """
        ctx     = Context()
        header  = MsgHeader.decode(ctx, raw)
        fields  = asdict(header) #type: ignore
        options = read_options(ctx, raw)
        return cls(options=options, **fields)

@dataclass(repr=False)
class RelayForwardMessage(RelayReplyMessage):
    op:        MessageType
    hops:      int
    link_addr: IpType
    peer_addr: IpType
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
        header  = MsgHeader.decode(ctx, raw)
        options = read_options(ctx, raw)
        return cls(
            op=header.op, 
            hops=header.hops, 
            link_addr=header.link_addr, 
            peer_addr=header.peer_addr, 
            options=options
        )
