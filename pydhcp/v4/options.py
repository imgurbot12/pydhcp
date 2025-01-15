"""
DHCPv4 Option Implementations
"""
from functools import lru_cache
from typing import ClassVar, List, Optional, Type
from typing_extensions import Annotated, Self

from pystructs import (
    I32, U16, U32, U8, Context, Domain, GreedyBytes,
    GreedyList, HintedBytes, IPv4, Struct)

from ..abc import DHCPOption
from ..enum import Arch, StatusCode

from .enum import MessageType, OptionCode

#** Variables **#
__all__ = [
    'pack_option',
    'unpack_option',

    'Option',
    'Unknown',

    'SubnetMask',
    'TimezoneOffset',
    'Router',
    'TimeServer',
    'INetNameServer',
    'DomainNameServer',
    'LogServer',
    'QuoteServer',
    'LPRServer',
    'Hostname',
    'DomainName',
    'BroadcastAddr',
    'VendorInfo',
    'RequestedIPAddr',
    'IPLeaseTime',
    'DHCPMessageType',
    'ServerIdentifier',
    'ParamRequestList',
    'DHCPMessage',
    'MaxMessageSize',
    'RenewalTime',
    'RebindTime',
    'VendorClassIdentifier',
    'TFTPServerName',
    'DHCPStatusCode',
    'BootfileName',
    'ClientSystemArch',
    'DNSDomainSearchList',
    'TFTPServerIP',
    'PXEPathPrefix',
    'End',
]

ByteContent   = Annotated[bytes, GreedyBytes()]
OptionCodeInt = Annotated[OptionCode, U8]

#** Functions **#

def pack_option(option: 'Option', ctx: Optional[Context] = None) -> bytes:
    """
    """
    return OptionHeader(option.opcode, option.pack()).pack(ctx)

def unpack_option(raw: bytes, ctx: Optional[Context] = None) -> 'Option':
    """
    """
    header = OptionHeader.unpack(raw, ctx)
    oclass = OPTION_MAP.get(header.opcode, None)
    oclass = oclass or Unknown.new(header.opcode, len(header.option))
    return oclass.unpack(header.option)

#** Classes **#

class OptionHeader(Struct):
    opcode: OptionCodeInt
    option: Annotated[bytes, HintedBytes(U8)]

class Option(Struct, DHCPOption):
    """
    Abstract Baseclass for DHCPv4 Option Content
    """
    opcode: ClassVar[OptionCode] #type: ignore

class _IPv4ListOption(Option):
    """
    BaseClass for AddressList Options
    """
    opcode: ClassVar[OptionCode]
    ips:    Annotated[List[IPv4], GreedyList(IPv4)]

class SubnetMask(Option):
    """
    SubnetMask (1) - The Subnet Mask to Apply for an Ipv4 Address Assignment
    """
    opcode: ClassVar[OptionCode] = OptionCode.SubnetMask
    mask:   IPv4

class TimezoneOffset(Option):
    """
    TimezoneOffset (2) - Informs Client of Network Timezone Offset
    """
    opcode: ClassVar[OptionCode] = OptionCode.TimeOffset
    offset: I32

class Router(_IPv4ListOption):
    """
    Router (3) - IPv4 Router/Gateway Addresses
    """
    opcode: ClassVar[OptionCode] = OptionCode.Router

class TimeServer(_IPv4ListOption):
    """
    TimeServer (4) - Network TimeServers
    """
    opcode: ClassVar[OptionCode] = OptionCode.TimeServer

class INetNameServer(_IPv4ListOption):
    """
    NameServer (5) - IEN 116 Name Servers (Deprecated/Legacy)
    """
    opcode: ClassVar[OptionCode] = OptionCode.NameServer

class DomainNameServer(_IPv4ListOption):
    """
    DomainNameServer (6) - Name Server Addresses (DNS)
    """
    opcode: ClassVar[OptionCode] = OptionCode.DomainNameServer

class LogServer(_IPv4ListOption):
    """
    LogServer (7) - MIT-LCS UDP log servers
    """
    opcode: ClassVar[OptionCode] = OptionCode.LogServer

class QuoteServer(_IPv4ListOption):
    """
    CookieServer (8) - Quote of The Day Server (RFC 865)
    """
    opcode: ClassVar[OptionCode] = OptionCode.QuoteServer

class LPRServer(_IPv4ListOption):
    """
    LPRServer (9) - Line Printer Server (RFC 1179)
    """
    opcode: ClassVar[OptionCode] = OptionCode.LPRServer

class Hostname(Option):
    """
    Hostname (12) - Client Hostname Assignment
    """
    opcode:   ClassVar[OptionCode] = OptionCode.HostName
    hostname: ByteContent

class DomainName(Option):
    """
    DomainName (15) - DNS Resolution Domain for Client
    """
    opcode: ClassVar[OptionCode] = OptionCode.DomainName
    domain: ByteContent

class BroadcastAddr(Option):
    """
    BroadCastAddress (28) - Specifies Network Broadcast Address
    """
    opcode: ClassVar[OptionCode] = OptionCode.BroadcastAddress
    addr:   IPv4

class VendorInfo(Option):
    """
    Vendor Specific Information (43) - Arbitrary Vendor Data over DHCP
    """
    opcode: ClassVar[OptionCode] = OptionCode.VendorSpecificInformation
    info:   ByteContent

class RequestedIPAddr(Option):
    """
    Requested IP Address (50) - Client Requested IP Address
    """
    opcode: ClassVar[OptionCode] = OptionCode.RequestedIPAddress
    ip:     IPv4

class IPLeaseTime(Option):
    """
    IPLeaseTime (51) - Client Requested/Server Assigned Lease Time
    """
    opcode:  ClassVar[OptionCode] = OptionCode.IPAddressLeaseTime
    seconds: U32

class DHCPMessageType(Option):
    """
    DHCP Message Type (53) - Declares DHCP Message Type
    """
    opcode: ClassVar[OptionCode] = OptionCode.DHCPMessageType
    mtype:  Annotated[MessageType, U8]

class ServerIdentifier(Option):
    """
    DHCP Server Identifier (54) - Identifies DHCP Server Subject
    """
    opcode: ClassVar[OptionCode] = OptionCode.ServerIdentifier
    ip:     IPv4

class ParamRequestList(Option):
    """
    DHCP Parameter Request List (55) - DHCP Request for Specified Options
    """
    opcode: ClassVar[OptionCode] = OptionCode.ParameterRequestList
    params: Annotated[List[OptionCode], GreedyList(OptionCodeInt)]

class DHCPMessage(Option):
    """
    Server Message (56) - DCHP Message on Server Error / Rejection
    """
    opcode:  ClassVar[OptionCode] = OptionCode.Message
    message: ByteContent

class MaxMessageSize(Option):
    """
    DHCP Max Message Size (57) - Maximum Length Packet Sender will Accept
    """
    opcode: ClassVar[OptionCode] = OptionCode.Message
    size:   U16

class RenewalTime(Option):
    """
    DHCP Renewal Time (58) - Client Address Renewal Interval
    """
    opcode:  ClassVar[OptionCode] = OptionCode.RenewTimeValue
    seconds: U32

class RebindTime(Option):
    """
    DHCP Rebind Time (59) - Client Address Rebind Interval
    """
    opcode:  ClassVar[OptionCode] = OptionCode.RebindingTimeValue
    seconds: U32

class VendorClassIdentifier(Option):
    """
    Vendor Class Identifier (60) - Optionally Identify Vendor Type and Config
    """
    opcode: ClassVar[OptionCode] = OptionCode.ClassIdentifier
    vendor: ByteContent

class TFTPServerName(Option):
    """
    TFTP Server Name (66) - TFTP Server Option when `sname` field is reserved
    """
    opcode: ClassVar[OptionCode] = OptionCode.TFTPServerName
    name:   ByteContent

class BootfileName(Option):
    """
    Bootfile Name (67) - Bootfile Assignment with `file` field is reserved
    """
    opcode: ClassVar[OptionCode] = OptionCode.BootfileName
    name:   ByteContent

class ClientSystemArch(Option):
    """
    Client System Architecture (93) - Declare PXE Client Arch (RFC 4578)
    """
    opcode: ClassVar[OptionCode] = OptionCode.ClientSystemArchitectureType
    arches: Annotated[List[Arch], GreedyList(Annotated[Arch, U16])]

class DNSDomainSearchList(Option):
    """
    DNS Domain Search List (119) - List of DNS Search Domain Suffixes (RFC 3397)
    """
    opcode:  ClassVar[OptionCode] = OptionCode.DNSDomainSearchList
    domains: Annotated[List[bytes], GreedyList(Domain)]

class TFTPServerIP(Option):
    """
    TFTP Server IP Address (128) - Commonly used for TFTP Server IP Address
    """
    opcode: ClassVar[OptionCode] = OptionCode.TFTPServerIPAddress
    ip:     ByteContent

class DHCPStatusCode(Option):
    """
    DHCP Status Code (151) - DHCP Server Response Status Code (RFC 6926)
    """
    opcode:  ClassVar[OptionCode] = OptionCode.StatusCode
    value:   Annotated[StatusCode, U8]
    message: Annotated[bytes, GreedyBytes()]

class PXEPathPrefix(Option):
    """
    PXE Server Path Prefix (210) - PXELINUX TFTP Path Prefix (RFC 5071)
    """
    opcode: ClassVar[OptionCode] = OptionCode.TFTPServerIPAddress
    prefix: ByteContent

class End(Option):
    """
    END (255) - Indicates End of DHCP Options List
    """
    opcode: ClassVar[OptionCode] = OptionCode.End

class Unknown:
    """
    Mock Option Object for Unknown/Unsupported DHCP Content Types
    """
    __slots__ = ('data', )

    opcode: ClassVar[OptionCode]
    size:   ClassVar[int]

    def __init__(self, data: bytes):
        self.data = data

    def __repr__(self) -> str:
        return f'Unknown(opcode={self.opcode!r}, data=0x{self.data.hex()})'

    def pack(self, ctx: Optional[Context] = None) -> bytes:
        ctx = ctx or Context()
        return ctx.track_bytes(self.data)

    @classmethod
    def unpack(cls, raw: bytes, ctx: Optional[Context] = None) -> Self:
        ctx = ctx or Context()
        return cls(ctx.slice(raw, cls.size))

    @classmethod
    @lru_cache(maxsize=None)
    def new(cls, opcode: OptionCode, size: int) -> Type:
        return type('Unknown', (cls, ), {'opcode': opcode, 'size': size})

#** Init **#

#: cheeky way of collecting all option types into map based on their OptionCode
OPTION_MAP = {v.opcode:v
    for v in globals().values()
    if isinstance(v, type) and issubclass(v, Option) and hasattr(v, 'opcode')}
