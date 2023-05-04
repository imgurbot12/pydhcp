"""
DHCPv4 Backend Implementation
"""
from abc import abstractmethod
from datetime import timedelta
from ipaddress import IPv4Address, IPv4Interface
from typing import NamedTuple, Protocol, ClassVar, List, Tuple, Any

#** Variables **#
__all__ = [
    'Assignment',
    'Answer',
    'Backend',

    'Cache',
]

Items = List[Tuple[str, Any]]

#** Functions **#

def repr_items(name: str, items: Items) -> str:
    """render items for `Assignment` and `Answer`"""
    values = ', '.join(f'{k}={v}' for k,v in items)
    return f'{name}({values})'

def summary_items(items: Items, join: str, prefix: str) -> str:
    return join.join(f'{prefix}{k}={v}' for k,v in items)

#** Classes **#

class Assignment(NamedTuple):
    """
    DHCPv4 Client Assignment Details
    """
    client:  IPv4Interface
    dns:     IPv4Address
    gateway: IPv4Address
    lease:   timedelta
    
    def __repr__(self) -> str:
        return repr_items('Assign', self.items())

    def items(self) -> List[Tuple[str, Any]]:
        return [
            ('ip', self.client),
            ('gw', self.gateway),
            ('dns', self.dns),
            ('lease', self.lease),
        ]

    def summary(self, prefix: str = '', join: str = '\n') -> str:
        return summary_items(self.items(), join, prefix)

    @property
    def your_addr(self) -> IPv4Address:
        """retrieve client-ip from given client ip-config"""
        return self.client.ip

    @property
    def netmask(self) -> IPv4Address:
        """retrieve netmask for the given client ip-config"""
        return self.client.netmask

    @property
    def broadcast(self) -> IPv4Address:
        """guess broadcast address based on ip/netmask"""
        ipiter    = zip(self.your_addr.packed, self.netmask.packed)
        broadcast = bytes(o if b == 255 else 255 for o,b in ipiter)
        return IPv4Address(broadcast)

    @property
    def lease_seconds(self) -> int:
        """retrieve lease in seconds as an integer"""
        return int(self.lease.total_seconds())

class Answer(NamedTuple):
    assign: Assignment
    source: str
 
    def items(self) -> List[Tuple[str, Any]]:
        return [*self.assign.items(), ('src', self.source)]
    
    def summary(self, prefix: str = '', join: str = '\n') -> str:
        return summary_items(self.items(), join, prefix)

    def __repr__(self) -> str:
        return repr_items('Answer', self.items())

class Backend(Protocol):
    """
    BaseClass Interface Definition for Backend Implementatons
    """
    source: ClassVar[str]

    @abstractmethod
    def get_assignment(self, hwaddr: bytes) -> Answer:
        raise NotImplementedError

    @abstractmethod
    def del_assignment(self, hwaddr: bytes):
        raise NotImplementedError

#** Imports **#
from .cache import Cache
