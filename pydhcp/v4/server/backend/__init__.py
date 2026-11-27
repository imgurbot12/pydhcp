"""
DHCP Server Data Backend Implementations
"""
from abc import abstractmethod
from typing import ClassVar, Optional, Protocol

from pyderive import dataclass
from pyserve import Address

from ... import Message

#** Variables **#
__all__ = [
    'Address',
    'Answer',
    'Backend',

    'Cache',
    'MemoryBackend',

    'PxeTftpConfig',
    'PxeDynConfig',
    'PxeConfig',
    'PXEBackend',

    'SimpleAnswer',
    'SimpleBackend',
    'SingleFlight',
]

#** Classes **#

@dataclass(slots=True)
class Answer:
    """
    Backend DNS Answers Return Type
    """
    message:      Message
    source:       str
    source_label: Optional[str] = None

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
from .cache import Cache
from .memory import MemoryBackend
from .pxe import PxeTftpConfig, PxeDynConfig, PxeConfig, PXEBackend
from .simple import SimpleAnswer, SimpleBackend
from .single import SingleFlight
