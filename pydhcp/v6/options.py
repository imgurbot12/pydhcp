"""
DHCPv6 Option Implementations
"""
from typing import ClassVar
from typing_extensions import Annotated, Self

from pystructs import *
from pyderive import dataclass

from .duid import DUID, read_duid, write_duid
from .enum import OptionCode
from ..enum import StatusCode
from ..base import DHCPOption, DHCPOptionList, Microseconds, Seconds

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
OptionCodeInt = Annotated[OptionCode, Wrap[U16, OptionCode]]

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

class OptStruct(Struct):
    code:  OptionCodeInt
    value: Annotated[bytes, SizedBytes[U16]]

class Option(DHCPOption):
    """DHCPv6 BaseClass Option Definition"""
    opcode: ClassVar[OptionCode] = OptionCode.UNKNOWKN

class OptionList(DHCPOptionList):
    """DHCPv6 DHCPOptionList Implementation"""
    pass

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

class OptNonTemporaryAddr(Option):
    opcode = OptionCode.NonTemporaryAddress
    value:   U32
    t1:      U32
    t2:      U32
    options: GreedyBytes

class OptTemporaryAddress(Option):
    opcode = OptionCode.TemporaryAddress
    value:   U32
    options: GreedyBytes

class OptAddress(Option):
    opcode = OptionCode.Address
    value:          IPv6
    pref_lifetime:  Annotated[Seconds, Wrap[U32, Seconds]]
    valid_lifetime: Annotated[Seconds, Wrap[U32, Seconds]]
    options:        GreedyBytes

class OptRequestList(Option):
    opcode = OptionCode.OptionRequest
    value: GreedyList[OptionCodeInt]

class OptPreference(Option):
    opcode = OptionCode.Preference
    value: U8

class OptElapsed(Option):
    opcode = OptionCode.ElapsedTime
    value: Annotated[Microseconds, Wrap[U16, Microseconds]]

class OptRelay(Option):
    opcode = OptionCode.RelayMessage
    value: GreedyBytes

class OptAuth(Option):
    value: ClassVar[int] # remove value as init-arg
    opcode = OptionCode.Authentication
    protocol:   U8
    algorithm:  U8
    rdm:        U8
    replay_det: StaticBytes[8]
    info:       GreedyBytes

class OptUnicast(Option):
    opcode = OptionCode.ServerUnicast
    value: IPv6

class OptStatusCode(Option):
    opcode = OptionCode.StatusCode
    value:   Annotated[StatusCode, Wrap[U16, StatusCode]]
    message: GreedyBytes

class OptIdAssocPrefixDeleg(Option):
    opcode = OptionCode.IdAssocPrefixDeleg
    value:   U32
    t1:      Annotated[Seconds, Wrap[U32, Seconds]]
    t2:      Annotated[Seconds, Wrap[U32, Seconds]]
    options: GreedyBytes
 
    def read_options(self) -> OptionList:
        ctx = Context()
        options = OptionList()
        while ctx.index < len(self.options):
            option = read_option(ctx, self.options)
            options.append(option)
        return options

class OptIAPrefix(Option):
    value: ClassVar[int]
    opcode = OptionCode.IAPrefix
    pref_lifetime:  Annotated[Seconds, Wrap[U32, Seconds]]
    valid_lifetime: Annotated[Seconds, Wrap[U32, Seconds]]
    prefix_length:  U8
    ipv6_prefix:    IPv6
    options:        GreedyBytes

#** Init **#

#: map of option-codes to option-subclasses
OPTIONS = {
    value.opcode:value
    for name, value in globals().items()
    if not name.startswith('_') and isinstance(value, type) and issubclass(value, Option) 
}
