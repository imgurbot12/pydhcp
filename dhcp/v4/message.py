"""
DHCPv4 Message Implementation
"""
from dataclasses import dataclass
from ipaddress import IPv4Address
from typing import Union, List, Optional
from typing_extensions import Self

from pystructs import *

from .enum import MessageType, OpCode, OptionCode
from .options import OptionList, read_option
from ..enum import HwType

#** Variables **#
__all__ = ['Message']

#: magic cookie to include in DHCP message
MAGIC_COOKIE = bytes([0x63, 0x82, 0x53, 0x63])

#: zeroed ip-address default for message values
ZeroIp = IPv4Address('0.0.0.0')

#: valid types supported for ip-address assignment
IpType = Union[str, bytes, IPv4Address]

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

@struct
class Header:
    """DHCPv4 Message Header Group"""
    opcode:       Int[8, OpCode, 'OpCode']
    hw_type:      Int[8, HwType, 'HwType'] 
    hw_length:    Int8
    hops:         Int8
    message_id:   Int32
    seconds:      Int16
    flags:        Int16
    client_addr:  Ipv4
    your_addr:    Ipv4
    server_addr:  Ipv4
    gateway_addr: Ipv4
    hw_addr:      StaticBytes[16]
    server_name:  StaticBytes[64]
    boot_file:    StaticBytes[128]
    magic_cookie: Const[MAGIC_COOKIE]

@dataclass(repr=False)
class Message:
    op:           OpCode
    id:           int
    client_hw:    bytes
    options:      OptionList
    hw_type:      HwType = HwType.Ethernet
    hops:         int    = 0
    seconds:      int    = 0
    flags:        int    = 0
    client_addr:  IpType = ZeroIp
    your_addr:    IpType = ZeroIp
    server_addr:  IpType = ZeroIp
    gateway_addr: IpType = ZeroIp 
    server_name:  bytes  = b''
    boot_file:    bytes  = b''
 
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
            hw_length=6, #TODO: this might need to be dynamic somehow
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
            data += option.encode(ctx)
        if not any(opt.opcode == OptionCode.End for opt in self.options):
            data += b'\x00'
        return bytes(data)

    @classmethod
    def decode(cls, raw: bytes) -> Self:
        """
        deserialize encoded DHCP Message into Message object
        """
        ctx     = Context()
        header  = Header.decode(ctx, raw)
        options = OptionList()
        while raw[ctx.index] != 0:
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
