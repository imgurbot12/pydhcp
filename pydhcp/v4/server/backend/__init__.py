"""
DHCPv4 Backend Implementation
"""
from abc import abstractmethod
from datetime import timedelta
from ipaddress import IPv4Address, IPv4Interface
from typing import NamedTuple, Protocol, ClassVar

#** Variables **#
__all__ = [
    'Assignment',
    'Answer',
    'Backend',

    'Cache',
]

#** Classes **#

class Assignment(NamedTuple):
    """
    DHCPv4 Client Assignment Details
    """
    client:  IPv4Interface
    dns:     IPv4Address
    gateway: IPv4Address
    lease:   timedelta
 
    @property
    def your_addr(self) -> IPv4Address:
        return self.client.ip

    @property
    def netmask(self) -> IPv4Address:
        return self.client.netmask

class Answer(NamedTuple):
    assign: Assignment
    source: str

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
