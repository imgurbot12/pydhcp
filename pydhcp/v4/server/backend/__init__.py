"""
DHCP Server Data Backend Implementations
"""
from abc import abstractmethod
from typing import ClassVar, NamedTuple, Optional, Protocol

from pyserve import Address

from ... import Message

#** Variables **#
__all__ = [
    'Address',
    'Answer',
    'Backend',

    'CacheBackend',
    'MemoryBackend',

    'PxeTftpConfig',
    'PxeDynConfig',
    'PxeConfig',
    'PXEBackend',

    'SimpleAnswer',
    'SimpleBackend',
]

#** Classes **#

class Answer(NamedTuple):
    """
    Backend DNS Answers Return Type
    """
    message: Message
    source:  str

class Backend(Protocol):
    """
    Base-class Interface Definition for Backend Implementations
    """
    source: ClassVar[str]

    @abstractmethod
    async def discover(self, address: Address, request: Message) -> Optional[Answer]:
        """
        Process DHCP DISCOVER Message and Send Response

        :param address: client address
        :param request: dhcp request message
        :return:        dhcp response message
        """
        raise NotImplementedError

    @abstractmethod
    async def request(self, address: Address, request: Message) -> Optional[Answer]:
        """
        Process DHCP REQUEST Message and Send Response

        :param address: client address
        :param request: dhcp request message
        :return:        dhcp response message
        """
        raise NotImplementedError

    @abstractmethod
    async def decline(self, address: Address, request: Message) -> Optional[Answer]:
        """
        Process DHCP DECLINE Message and Send Response

        :param address: client address
        :param request: dhcp request message
        :return:        dhcp response message
        """
        raise NotImplementedError

    @abstractmethod
    async def release(self, address: Address, request: Message) -> Optional[Answer]:
        """
        Process DHCP RELEASE Message and Send Response

        :param address: client address
        :param request: dhcp request message
        :return:        dhcp response message
        """
        raise NotImplementedError

#** Imports **#
from .cache import *
from .memory import *
from .pxe import *
from .simple import *
