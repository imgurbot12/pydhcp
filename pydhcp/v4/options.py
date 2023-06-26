"""
DHCPv4 Option Implementations
"""
from typing import ClassVar, List, SupportsInt
from typing_extensions import Annotated
from warnings import warn

from pystructs import *
from pyderive import dataclass

from .enum import OptionCode, MessageType
from ..enum import Arch, StatusCode
from ..base import DHCPOption, DHCPOptionList, Seconds

#** Variables **#
__all__ = [
    'read_option',

    'Option',
    'OptionList',
    'OptEnd',
    'OptServerId',
    'OptSubnetMask',
    'OptBroadcast',
    'OptRouter',
    'OptDNS',
    'OptRequestedAddr',
    'OptStatusCode',
    'OptIPLeaseTime',
    'OptRenwalTime',
    'OptRebindTime',
    'OptMessageType',
    'OptParamRequestList',
    'OptMaxMessageSize',
    'OptClassIdentifier',
    'OptTFTPServerName',
    'OptTFTPServerIP',
    'OptBootFile',
    'OptPXEPathPrefix',
    'OptUserClassInfo',
    'OptClientSystemArch',
    'OptClientNetworkIface',
    'OptClientMachineID',
    'OptEtherBoot',
]

#: codec to parse Int8 as OptionCode
OptionCodeInt = Annotated[OptionCode, Wrap[U8, OptionCode]]

#** Functions **#

def read_option(ctx: Context, raw: bytes) -> 'Option':
    """
    read and deserialize best option-class to match option content
    
    :param ctx: serialization context
    :param raw: raw bytes to deserialized into an option
    :return:    option object
    """
    # parse option-type/value & retrieve best matching subclass
    opt     = OptStruct.decode(ctx, raw)
    oclass  = OPTIONS.get(opt.code, Option)
    # parse option w/ it's own sub-context
    subctx = Context()
    option = oclass.decode(subctx, opt.value)
    if oclass is Option:
        oclass.opcode = opt.code
    return option

def write_option(ctx: Context, option) -> bytes:
    """
    write and serialize option-class into raw-bytes
    
    :param ctx: serialization context
    :param raw: option object to serialize
    :return:    serialized bytes
    """
    # serialize option into bytes
    subctx  = Context()
    content = option.encode(subctx)
    return OptStruct(option.opcode, content).encode(ctx)

#** Classes **#

class OptStruct(Struct):
    code:  OptionCodeInt
    value: Annotated[bytes, SizedBytes[U8]]
 
    def __post_init__(self):
        """warn when value is too long and truncate"""
        if len(self.value) <= 255:
            return
        code       = self.code
        vlen       = len(self.value)
        self.value = self.value[:252] + b'...'
        warn(f'{code!r} value too long {vlen}. truncating!', RuntimeWarning)

@dataclass
class Option(DHCPOption):
    """DHCPv4 BaseClass Option Definition"""
    opcode: ClassVar[OptionCode] = OptionCode.OptionPad

class OptionList(DHCPOptionList):
    """DHCPv4 DHCPOptionList Implementation"""
    pass

### SubClasses

class OptEnd(Option):
    opcode = OptionCode.End

class OptHostName(Option):
    opcode = OptionCode.HostName

class _Ipv4Option(Option):
    opcode: ClassVar[OptionCode]
    value:  IPv4

class OptServerId(_Ipv4Option):
    opcode = OptionCode.ServerIdentifier

class OptSubnetMask(_Ipv4Option):
    opcode = OptionCode.SubnetMask

class OptBroadcast(_Ipv4Option):
    opcode = OptionCode.BroadcastAddress

class OptRouter(_Ipv4Option):
    opcode = OptionCode.Router

class OptDNS(_Ipv4Option):
    opcode = OptionCode.DomainNameServer
    value: Annotated[List[Ipv4Type], GreedyList[IPv4]]

class OptRequestedAddr(_Ipv4Option):
    opcode = OptionCode.RequestedIPAddress

class OptStatusCode(Option):
    opcode = OptionCode.StatusCode
    value:   Annotated[StatusCode, Wrap[U8, StatusCode]]
    message: GreedyBytes

class OptIPLeaseTime(Option):
    opcode = OptionCode.IPAddressLeaseTime
    value: Annotated[SupportsInt, Wrap[U32, Seconds]]

class OptRenwalTime(Option):
    opcode = OptionCode.RenewTimeValue
    value: Annotated[SupportsInt, Wrap[U32, Seconds]]

class OptRebindTime(Option):
    opcode = OptionCode.RenewTimeValue
    value: Annotated[SupportsInt, Wrap[U32, Seconds]]

class OptMessageType(Option):
    opcode = OptionCode.DHCPMessageType
    value: Annotated[MessageType, Wrap[U8, MessageType]]

class OptParamRequestList(Option):
    opcode = OptionCode.ParameterRequestList
    value: Annotated[OptionCode, GreedyList[OptionCodeInt]]

class OptMaxMessageSize(Option):
    opcode = OptionCode.MaximumDHCPMessageSize
    value: U16

class OptClassIdentifier(Option):
    opcode = OptionCode.ClassIdentifier

class OptTFTPServerName(Option):
    opcode = OptionCode.TFTPServerName

class OptTFTPServerIP(_Ipv4Option):
    opcode = OptionCode.TFTPServerIPAddress

class OptBootFile(Option):
    opcode = OptionCode.BootfileName

class OptPXEPathPrefix(Option):
    opcode = OptionCode.PXELinuxPathPrefix

class OptUserClassInfo(Option):
    opcode = OptionCode.UserClassInformation

class OptClientSystemArch(Option):
    opcode = OptionCode.ClientSystemArchitectureType
    value: Annotated[List[Arch], GreedyList[Wrap[U16, Arch]]]

class OptClientNetworkIface(Option):
    opcode = OptionCode.ClientNetworkInterfaceIdentifier
    value: Const[b'\x01']
    major: U8
    minor: U8

class OptClientMachineID(Option):
    opcode = OptionCode.ClientMachineIdentifier
    value:  GreedyBytes

class OptEtherBoot(Option):
    opcode = OptionCode.Etherboot

#** Init **#

#: map of option-codes to option-subclasses
OPTIONS = {
    value.opcode:value
    for value in globals().values()
    if isinstance(value, type) and issubclass(value, Option) 
}
