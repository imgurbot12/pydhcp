"""
BaseClass ABC Protocol Implementations for DHCP v4/v6
"""
from enum import IntEnum
from datetime import timedelta
from typing import *
from typing_extensions import Annotated

from pystructs import Codec, Struct, GreedyBytes

#** Variables **#
__all__ = ['Seconds', 'Microseconds', 'DHCPOption', 'DHCPOptionList']

#** Classes **#

class Timedelta(timedelta):
    """Integer Codec Compatable Timedelta"""
    field: str = 'seconds'

    def __class_getitem__(cls, field: str):
        return type(field.title(), (cls, ), {'field': field})

    def __new__(cls, delta: SupportsInt = 0):
        return super().__new__(cls, **{cls.field: int(delta)})

    def __int__(self) -> int:
        return int(self.total_seconds())

Seconds      = Timedelta['seconds']
Microseconds = Timedelta['microseconds']

class DHCPOption(Struct):
    opcode: ClassVar[IntEnum]
    value:  Annotated[Codec, GreedyBytes]

class DHCPOptionList:
    """Hybrid Between Dict/List for Quick Option Collection"""

    def __init__(self, data: Optional[List[DHCPOption]] = None):
        self.data    = []
        self.opcodes = set()
        self.extend(data or [])

    def keys(self) -> Iterator[IntEnum]:
        return (option.opcode for option in self.data)

    def values(self) -> Iterator[DHCPOption]:
        return (option for option in self.data)

    def items(self) -> Iterator[Tuple[IntEnum, DHCPOption]]:
        return iter((option.opcode, option) for option in self.data)

    def __repr__(self) -> str:
        return repr(self.data)

    def __iter__(self) -> Iterator[DHCPOption]:
        yield from self.values()

    def __contains__(self, key: Union[IntEnum, DHCPOption]) -> bool:
        key = key.opcode if isinstance(key, DHCPOption) else key
        return key in self.opcodes

    def __getitem__(self, op: IntEnum):
        if op not in self.opcodes:
            raise KeyError(op)
        for option in self.data:
            if option.opcode == op:
                return option
        raise KeyError(op)

    def __setitem__(self, op: IntEnum, value: DHCPOption):
        if op not in self.opcodes:
            self.opcodes.add(op)
            self.data.append((op, value))
            return
        for n, option in enumerate(self.data, 0):
            if option.opcode == op:
                self.data[n] = value
                return
        raise AttributeError(f'Failed to set {op!r}')

    def get(self, key: IntEnum, default: Any = None):
        if key not in self.opcodes:
            return default
        return self[key]

    def set(self, option: DHCPOption):
        self[option.opcode] = option

    def setdefault(self, option: DHCPOption):
        if option.opcode not in self.opcodes:
            self.append(option)

    def sort(self):
        self.data.sort(key=lambda option: option.opcode)

    def append(self, option: DHCPOption):
        if option.opcode in self.opcodes:
            raise ValueError(f'Option: {option.opcode!r} already present')
        self.data.append(option)
        self.opcodes.add(option.opcode)

    def extend(self, options: Sequence[DHCPOption]):
        for opt in options:
            self.append(opt)

    def insert(self, pos: int, option: DHCPOption):
        if option.opcode in self.opcodes:
            raise ValueError(f'Option: {option.opcode} already present')
        self.data.insert(pos, option)
        self.opcodes.add(option.opcode)

    def index(self, key: IntEnum):
        if key not in self.opcodes:
            raise ValueError(f'Option: {key} not present')
        for n, opcode in enumerate(self.keys(), 0):
            if opcode == key:
                return n
        raise ValueError(f'Failed to Index: {key}')

    def move_to_start(self, key: IntEnum):
        index = self.index(key)
        item  = self.data.pop(index)
        self.opcodes.remove(key)
        self.insert(0, item)
