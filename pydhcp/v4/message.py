"""
DHCPv4 Message Implementation
"""
from ipaddress import IPv4Address
from typing import List, Optional
from typing_extensions import Annotated, Self

from pystructs import *
from pyderive import dataclass

from .enum import MessageType, OpCode, OptionCode
from .options import OptionList, read_option, write_option
from ..enum import HwType

#** Variables **#
__all__ = ['Message']

#: magic cookie to include in DHCP message
MAGIC_COOKIE = bytes([0x63, 0x82, 0x53, 0x63])

#: zeroed ip-address default for message values
ZeroIp = IPv4Address('0.0.0.0')

#** Functions **#

def get_ip(op: OptionCode, options: OptionList) -> Optional[IPv4Address]:
    """translate option value into ipv4-address"""
    option = options.get(op)
    if not option:
        return
    ip = option.value
    if not isinstance(ip, IPv4Address):
        ip = IPv4Address(ip)
    return ip

#** Classes **#

class Header(Struct):
    """DHCPv4 Message Header Group"""
    opcode:       Annotated[OpCode, Wrap[U8, OpCode]]
    hw_type:      Annotated[HwType, Wrap[U8, HwType]]
    hw_length:    U8
    hops:         U8
    message_id:   U32
    seconds:      U16
    flags:        U16
    client_addr:  IPv4
    your_addr:    IPv4
    server_addr:  IPv4
    gateway_addr: IPv4
    hw_addr:      Annotated[bytes, StaticBytes[16]]
    server_name:  Annotated[bytes, StaticBytes[64]]
    boot_file:    Annotated[bytes, StaticBytes[128]]
    magic_cookie: Annotated[bytes, Const[MAGIC_COOKIE]] = MAGIC_COOKIE

@dataclass(slots=True, repr=False)
class Message:
    op:           OpCode
    id:           int
    client_hw:    bytes
    options:      OptionList
    hw_type:      HwType   = HwType.Ethernet
    hops:         int      = 0
    seconds:      int      = 0
    flags:        int      = 0
    client_addr:  Ipv4Type = ZeroIp
    your_addr:    Ipv4Type = ZeroIp
    server_addr:  Ipv4Type = ZeroIp
    gateway_addr: Ipv4Type = ZeroIp 
    server_name:  bytes    = b''
    boot_file:    bytes    = b''
 
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        op    = self.op.name
        htype = self.hw_type.name 
        return f'{cname}(op={op}, id={self.id!r}, hwtype={htype})'
    
    def message_type(self) -> Optional[MessageType]:
        """
        retrieve message-type from options-list (if present)
        """
        option = self.options.get(OptionCode.DHCPMessageType)
        if option is not None:
            return option.value

    def requested_options(self) -> List[OptionCode]:
        """
        retrieve requested parameter options from options-list (if present)
        """
        option = self.options.get(OptionCode.ParameterRequestList)
        return [] if option is None else option.value

    def broadcast_address(self) -> Optional[IPv4Address]:
        """
        retrieve broadcast-address from options-list (if present)
        """
        return get_ip(OptionCode.BroadcastAddress, self.options)

    def requested_address(self) -> Optional[IPv4Address]:
        """
        retrieve requested-address from options-list (if present)
        """
        return get_ip(OptionCode.RequestedIPAddress, self.options)

    def server_identifier(self) -> Optional[IPv4Address]:
        """
        retrieve server-identifier from options-list (if present)
        """
        return get_ip(OptionCode.ServerIdentifier, self.options)

    def encode(self) -> bytes:
        """
        serialize DHCP Message as bytes to send via socket
        """
        ctx   = Context()
        data  = bytearray()
        data += Header(
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
            hw_addr=self.client_hw,
            server_name=self.server_name,
            boot_file=self.boot_file,
        ).encode(ctx)
        for option in self.options:
            data += write_option(ctx, option)
        if not any(opt.opcode == OptionCode.End for opt in self.options):
            data += bytes((OptionCode.End, ))
        return bytes(data)

    @classmethod
    def decode(cls, raw: bytes) -> Self:
        """
        deserialize encoded DHCP Message into Message object
        """
        ctx     = Context()
        header  = Header.decode(ctx, raw)
        options = OptionList()
        while raw[ctx.index] not in (0, OptionCode.End):
            option = read_option(ctx, raw)
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
