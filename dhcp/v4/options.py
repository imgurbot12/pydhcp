"""
DHCPv4 Option Implementations
"""
from dataclasses import dataclass
from typing import ClassVar
from typing_extensions import Self

from pystructs import *

from .enum import OptionCode, MessageType
from ..enum import Arch, StatusCode
from ..base import DHCPOption, DHCPOptionList, Timedelta

#** Variables **#
__all__ = [
    'read_option',

    'Option',
    'OptionList',
    'OptEnd',
    'OptSubnetMask',
    'OptRouter',
    'OptDNS',
    'OptRequestedAddr',
    'OptStatusCode',
    'OptIPLeaseTime',
    'OptMessageType',
    'OptParamRequestList',
    'OptMaxMessageSize',
    'OptClassIdentifier',
    'OptTFTPServerName',
    'OptTFTPServerIP',
    'OptBootFile',
    'OptUserClassInfo',
    'OptClientSystemArch',
    'OptClientNetworkIface',
    'OptClientMachineID',
    'OptEtherBoot',
]

#: codec to parse Int8 as OptionCode
OptionCodeInt = Int[8, OptionCode, 'OptionCode']

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

def write_option(ctx: Context, option: 'Option') -> bytes:
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

@struct
class OptStruct:
    code:  OptionCodeInt
    value: SizedBytes[8]

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

@struct
class _Ipv4Option(Option):
    opcode: ClassVar[OptionCode]
    value:  Ipv4

class OptServerId(_Ipv4Option):
    opcode = OptionCode.ServerIdentifier

class OptSubnetMask(_Ipv4Option):
    opcode = OptionCode.SubnetMask

class OptRouter(_Ipv4Option):
    opcode = OptionCode.Router

class OptDNS(_Ipv4Option):
    opcode = OptionCode.DomainNameServer

class OptRequestedAddr(_Ipv4Option):
    opcode = OptionCode.RequestedIPAddress

@struct
class OptStatusCode(Option):
    opcode = OptionCode.StatusCode
    value:   Int[8, StatusCode, 'StatusCode']
    message: GreedyBytes

@struct
class OptIPLeaseTime(Option):
    opcode = OptionCode.IPAddressLeaseTime
    value: Int[32, Timedelta['seconds'], 'Lease']

@struct
class OptMessageType(Option):
    opcode = OptionCode.DHCPMessageType
    value: Int[8, MessageType, 'MessageType']

@struct
class OptParamRequestList(Option):
    opcode = OptionCode.ParameterRequestList
    value: GreedyList[OptionCodeInt]

@struct
class OptMaxMessageSize(Option):
    opcode = OptionCode.MaximumDHCPMessageSize
    value: Int16

class OptClassIdentifier(Option):
    opcode = OptionCode.ClassIdentifier

class OptTFTPServerName(Option):
    opcode = OptionCode.TFTPServerName

class OptTFTPServerIP(Option):
    opcode = OptionCode.TFTPServerIPAddress

class OptBootFile(Option):
    opcode = OptionCode.BootfileName

class OptUserClassInfo(Option):
    opcode = OptionCode.UserClassInformation

@struct
class OptClientSystemArch(Option):
    opcode = OptionCode.ClientSystemArchitectureType
    value: GreedyList[Int[16, Arch, 'Arch']]

@struct
class OptClientNetworkIface(Option):
    opcode = OptionCode.ClientNetworkInterfaceIdentifier
    value: Const[b'\x01']
    major: Int8
    minor: Int8

@struct
class OptClientMachineID(Option):
    opcode = OptionCode.ClientMachineIdentifier
    prefix: Const[b'\x00']
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
