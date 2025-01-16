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
    BaseClass Interface Definition for Backend Implementations
    """
    source: ClassVar[str]

    @abstractmethod
    def discover(self, address: Address, request: Message) -> Optional[Answer]:
        """
        Process DHCP DISCOVER Message and Send Response

        :param address: client address
        :param request: dhcp request message
        :return:        dhcp response message
        """
        raise NotImplementedError

    @abstractmethod
    def request(self, address: Address, request: Message) -> Optional[Answer]:
        """
        Process DHCP REQUEST Message and Send Response

        :param address: client address
        :param request: dhcp request message
        :return:        dhcp response message
        """
        raise NotImplementedError

    def decline(self, address: Address, request: Message) -> Optional[Answer]:
        """
        Process DHCP DECLINE Message and Send Response

        :param address: client address
        :param request: dhcp request message
        :return:        dhcp response message
        """
        raise NotImplementedError

    @abstractmethod
    def release(self, address: Address, request: Message) -> Optional[Answer]:
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
