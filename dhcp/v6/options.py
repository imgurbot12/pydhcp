"""
DHCPv6 Option Implementations
"""
from dataclasses import dataclass
from typing import ClassVar
from typing_extensions import Self

from pystructs import *

from .duid import DUID, read_duid, write_duid
from .enum import OptionCode
from ..enum import StatusCode
from ..base import Timedelta, DHCPOption, DHCPOptionList

#** Variables **#
__all__ = [
    'read_option',

    'Option',
    'OptionList',
    'OptClientIdentifier',
    'OptServerIdentifier',
    'OptNonTemporaryAddr',
    'OptTemporaryAddress',
    'OptAddress',
    'OptRequestList',
    'OptPreference',
    'OptElapsed',
    'OptRelay',
    'OptAuth',
    'OptUnicast',
    'OptStatusCode',
    'OptIdAssocPrefixDeleg',
    'OptIAPrefix',
]

#: integer codec ot parse option-code
OptionCodeInt = Int[16, OptionCode, 'OptionCode']

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
    value: SizedBytes[16]

class Option(DHCPOption):
    """DHCPv6 BaseClass Option Definition"""
    opcode: ClassVar[OptionCode] = OptionCode.UNKNOWKN

class OptionList(DHCPOptionList):
    """DHCPv6 DHCPOptionList Implementation"""
    pass

@dataclass
class _DuidOption(Option):
    """BaseClass to Support DUID Option Implementations"""
    opcode: ClassVar[OptionCode]
    value:  DUID

    def encode(self, ctx: Context) -> bytes:
        return write_duid(self.value)

    @classmethod
    def decode(cls, ctx: Context, value: bytes) -> Self:
        return cls(read_duid(value))

class OptClientIdentifier(_DuidOption):
    opcode = OptionCode.ClientIdentifier

class OptServerIdentifier(_DuidOption):
    opcode = OptionCode.ServerIdentifier

@struct
class OptNonTemporaryAddr(Option):
    opcode = OptionCode.NonTemporaryAddress
    value:   Int32
    t1:      Int32
    t2:      Int32
    options: GreedyBytes

@struct
class OptTemporaryAddress(Option):
    opcode = OptionCode.TemporaryAddress
    value:   Int32
    options: GreedyBytes

@struct
class OptAddress(Option):
    opcode = OptionCode.Address
    value:          Ipv6
    pref_lifetime:  Int[32, Timedelta, 'PrefferedLifetime']
    valid_lifetime: Int[32, Timedelta, 'ValidLifetime']
    options:        GreedyBytes

@struct
class OptRequestList(Option):
    opcode = OptionCode.OptionRequest
    value: GreedyList[OptionCodeInt]

@struct
class OptPreference(Option):
    opcode = OptionCode.Preference
    value: Int8

@struct
class OptElapsed(Option):
    opcode = OptionCode.ElapsedTime
    value: Int[16, Timedelta['microseconds'], 'Elapsed']

@struct
class OptRelay(Option):
    opcode = OptionCode.RelayMessage
    value: GreedyBytes

@struct
class OptAuth(Option):
    value: ClassVar[int] # remove value as init-arg
    opcode = OptionCode.Authentication
    protocol:   Int8
    algorithm:  Int8
    rdm:        Int8
    replay_det: StaticBytes[8]
    info:       GreedyBytes

@struct
class OptUnicast(Option):
    opcode = OptionCode.ServerUnicast
    value: Ipv6

@struct
class OptStatusCode(Option):
    opcode = OptionCode.StatusCode
    value:   Int[16, StatusCode, 'StatusCode']
    message: GreedyBytes

@struct
class OptIdAssocPrefixDeleg(Option):
    opcode = OptionCode.IdAssocPrefixDeleg
    value:   Int32
    t1:      Int[32, Timedelta, 'T1']
    t2:      Int[32, Timedelta, 'T2']
    options: GreedyBytes
 
    def read_options(self) -> OptionList:
        ctx = Context()
        options = OptionList()
        while ctx.index < len(self.options):
            option = read_option(ctx, self.options)
            options.append(option)
        return options

@struct
class OptIAPrefix(Option):
    value: ClassVar[int]
    opcode = OptionCode.IAPrefix
    pref_lifetime:  Int[32, Timedelta, 'PrefLifetime']
    valid_lifetime: Int[32, Timedelta, 'ValidLifetime']
    prefix_length:  Int8
    ipv6_prefix:    Ipv6
    options:        GreedyBytes

#** Init **#

#: map of option-codes to option-subclasses
OPTIONS = {
    value.opcode:value
    for name, value in globals().items()
    if not name.startswith('_') and isinstance(value, type) and issubclass(value, Option) 
}
