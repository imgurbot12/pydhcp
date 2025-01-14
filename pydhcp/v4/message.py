"""

"""
from ipaddress import IPv4Address
from typing import List, Optional, Union, cast
from typing_extensions import Annotated, Self

from pyderive import dataclass
from pystructs import U16, U32, U8, Const, Context, IPv4, StaticBytes, Struct

from ..abc import OptionList
from .enum import MessageType, OpCode, HwType, OptionCode
from .options import *

#** Variables **#
__all__ = ['Message']

#: pre-converted default ip-address for dhcpv4 packet
ZeroIp = IPv4Address('0.0.0.0')

#: magic cookie to include in DHCP message
MAGIC_COOKIE = bytes((0x63, 0x82, 0x53, 0x63))

#** Classes **#

class HexBytes(bytes):
    def __repr__(self) -> str:
        return f'0x{self.hex()}'

class MessageHeader(Struct):
    opcode:       Annotated[OpCode, U8]
    hw_type:      Annotated[HwType, U8]
    hw_length:    U8
    hops:         U8
    message_id:   U32
    seconds:      U16
    flags:        U16
    client_addr:  IPv4
    your_addr:    IPv4
    server_addr:  IPv4
    gateway_addr: IPv4
    hw_addr:      Annotated[HexBytes, StaticBytes(16)]
    server_name:  Annotated[bytes, StaticBytes(64)]
    boot_file:    Annotated[bytes, StaticBytes(128)]
    magic_cookie: Annotated[bytes, Const(MAGIC_COOKIE)] = MAGIC_COOKIE

@dataclass(slots=True)
class Message:
    op:           OpCode
    id:           int
    client_hw:    bytes
    options:      OptionList[Option]
    hw_type:      HwType      = HwType.Ethernet
    hops:         int         = 0
    seconds:      int         = 0
    flags:        int         = 0
    client_addr:  IPv4Address = ZeroIp
    your_addr:    IPv4Address = ZeroIp
    server_addr:  IPv4Address = ZeroIp
    gateway_addr: IPv4Address = ZeroIp
    server_name:  bytes       = b''
    boot_file:    bytes       = b''

    def message_type(self) -> Optional[MessageType]:
        """
        """
        option = self.options.get(DHCPMessageType)
        return option.mtype if option else None

    def requested_options(self) -> List[OptionCode]:
        """
        """
        option = self.options.get(ParamRequestList)
        return option.params if option else []

    def requested_address(self) -> Optional[IPv4Address]:
        """
        """
        option = self.options.get(RequestedIPAddr)
        return option.ip if option else None

    def broadcast_address(self) -> Optional[IPv4Address]:
        """
        """
        option = self.options.get(BroadcastAddr)
        return option.addr if option else None

    def server_identifier(self) -> Optional[IPv4Address]:
        """
        """
        option = self.options.get(ServerIdentifier)
        return option.ip if option else None

    def pack(self, ctx: Optional[Context] = None) -> bytes:
        """
        """
        ctx   = ctx or Context()
        data  = bytearray()
        data += MessageHeader(
            opcode=self.op,
            hw_type=self.hw_type,
            hw_length=len(self.client_hw),
            hops=self.hops,
            message_id=self.id,
            seconds=self.seconds,
            flags=self.flags,
            client_addr=self.client_addr,
            your_addr=self.your_addr,
            server_addr=self.server_addr,
            gateway_addr=self.gateway_addr,
            hw_addr=cast(HexBytes, self.client_hw),
            server_name=self.server_name,
            boot_file=self.boot_file,
        ).pack(ctx)
        data += b''.join(pack_option(op, ctx) for op in self.options)
        if not any(op.opcode == OptionCode.End for op in self.options):
            data += bytes((OptionCode.End, ))
        return bytes(data)

    @classmethod
    def unpack(cls, raw: bytes, ctx: Optional[Context] = None) -> Self:
        """
        """
        ctx     = ctx or Context()
        header  = MessageHeader.unpack(raw, ctx)
        options = OptionList()
        while raw[ctx.index] not in (0, OptionCode.End):
            option = unpack_option(raw, ctx)
            options.append(option)
        return cls(
            op=header.opcode,
            id=header.message_id,
            client_hw=header.hw_addr,
            options=options,
            hw_type=header.hw_type,
            hops=header.hops,
            seconds=header.seconds,
            flags=header.flags,
            client_addr=header.client_addr,
            your_addr=header.your_addr,
            gateway_addr=header.gateway_addr,
            server_name=header.server_name,
            boot_file=header.boot_file,
        )
