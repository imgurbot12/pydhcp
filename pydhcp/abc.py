"""
Abstract Baseclasses and Collections for PyDHCP Library
"""
from abc import ABC
from enum import IntEnum
from typing import (
    Any, ClassVar, Generic, Iterable, Iterator, KeysView,
    List, Optional, Sequence, Set, Type, TypeVar, ValuesView, cast, overload)

#** Variables **#
__all__ = ['DHCPOption', 'OptionList']

O = TypeVar('O', bound='DHCPOption')
T = TypeVar('T', bound='DHCPOption')

#** Classes **#

class DHCPOption(ABC):
    opcode: ClassVar[IntEnum]

class OptionList(Sequence[O], Generic[O]):
    """
    Hybrid Between Dictionary/List for Quick DHCP Option Selection
    """

    def __init__(self, data: Sequence[O] = ()):
        self.data:    List[O]  = []
        self.opcodes: Set[int] = set()
        self.extend(data)

    def append(self, value: O) -> None:
        if value.opcode not in self.opcodes:
            self.opcodes.add(value.opcode)
            self.data.append(value)
            return
        for n, op in enumerate(self.data, 0):
            if op.opcode == value.opcode:
                self.data[n] = value
                return

    def extend(self, values: Iterable[O]) -> None:
        for op in values:
            self.append(op)

    def remove(self, value: O) -> None:
        self.data.remove(value)
        self.opcodes.remove(value.opcode)

    def find(self, value: Any,
        start: int = 0, stop: Optional[int] = None) -> Optional[int]:
        for n, op in enumerate(self.data[start:stop], start):
            if op == value:
                return n

    def index(self,
        value: Any, start: int = 0, stop: Optional[int] = None) -> int:
        index = self.find(value, start, stop)
        if index is not None:
            return index
        raise ValueError(f'{value!r} is not in list')

    def insert(self, index: int, value: O) -> None:
        idx = self.find(value)
        if idx is not None:
            self.data.remove(value)
        self.data.insert(index, value)
        self.opcodes.add(value.opcode)

    @overload
    def get(self, key: int, default: Any = None) -> Optional[O]:
        ...

    @overload
    def get(self, key: Type[T], default: Any = None) -> Optional[T]:
        ...

    def get(self, key, default = None):
        key = key.opcode if hasattr(key, 'opcode') else key
        return self[key] if key in self.opcodes else default

    def keys(self) -> KeysView[int]:
        return cast(KeysView, (op.opcode for op in self.data))

    def values(self) -> ValuesView[O]:
        return cast(ValuesView, iter(self.data))

    def setdefault(self, op: O, index: Optional[int] = None):
        if op.opcode in self.opcodes:
            return
        if index is None:
            return self.append(op)
        return self.insert(index, op)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.data!r})'

    def __iter__(self) -> Iterator[O]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __contains__(self, key: object, /) -> bool: #type: ignore
        key = key.opcode if isinstance(key, DHCPOption) else key
        return key in self.opcodes

    @overload
    def __getitem__(self, key: slice, /) -> List[O]:
        ...

    @overload
    def __getitem__(self, key: int, /) -> O:
        ...

    def __getitem__(self, key, /): #type: ignore
        if isinstance(key, slice):
            return self.data.__getitem__(key)
        key = key.opcode if isinstance(key, DHCPOption) else key
        if key not in self.opcodes:
            raise KeyError(key)
        for op in self.data:
            if op.opcode == key:
                return op
        raise KeyError(key)
