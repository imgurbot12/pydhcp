"""
BaseClass ABC Protocol Implementations for DHCP v4/v6
"""
from enum import IntEnum
from datetime import timedelta
from dataclasses import dataclass
from typing import ClassVar, Optional, List, Union, Iterator, Any
from typing_extensions import Self

from pystructs import Context, Struct

#** Variables **#
__all__ = ['Timedelta', 'DHCPOption', 'DHCPOptionList']

#** Classes **#

class Timedelta(timedelta):
    """Integer Codec Compatable Timedelta"""
    field: str = 'seconds'

    def __class_getitem__(cls, field: str):
        return type(field.title(), (cls, ), {'field': field})

    def __new__(cls, delta: int = 0):
        return super().__new__(cls, **{cls.field: delta})

    def __int__(self) -> int:
        return int(self.total_seconds())

@dataclass
class DHCPOption(Struct):
    opcode: ClassVar[IntEnum]
    value:  bytes

    def encode(self, ctx: Context) -> bytes:
        if hasattr(self, '__encoded__'):
            return super().encode(ctx)
        return self.value

    @classmethod
    def decode(cls, ctx: Context, raw: bytes) -> Self:
        if hasattr(cls, '__encoded__'):
            return super().decode(ctx, raw)
        return cls(raw)

class DHCPOptionList:
    """Hybrid Between Dict/List for Quick Option Collection"""

    def __init__(self, data: Optional[List[DHCPOption]] = None):
        self.data = {}
        self.extend(data or [])
    
    def __repr__(self) -> str:
        return repr(list(self.data.values()))

    def __iter__(self) -> Iterator[DHCPOption]:
        yield from self.data.values()

    def __getitem__(self, op: IntEnum):
        return self.data[op]
 
    def __contains__(self, key: Union[IntEnum, DHCPOption]) -> bool:
        key = key.opcode if isinstance(key, DHCPOption) else key
        return key in self.data

    def get(self, key: IntEnum, default: Any = None):
        return self.data.get(key, default)

    def append(self, option: DHCPOption):
        if option.opcode in self.data:
            raise ValueError(f'Option: {option.opcode!r} already present')
        self.data[option.opcode] = option

    def extend(self, options: List[DHCPOption]):
        for opt in options:
            self.append(opt)
