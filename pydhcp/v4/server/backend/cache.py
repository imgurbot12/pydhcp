"""
Backend Extension to support In-Memory Answer Caching
"""
from logging import Logger, getLogger
import math
from threading import Lock
import time
from typing import ClassVar, Dict, Optional, Set, cast

from pyderive import InitVar, dataclass, field

from . import Address, Answer, Backend
from ...enum import MessageType
from ...message import Message, ZeroIp
from ...options import DHCPStatusCode, IPLeaseTime
from ....enum import StatusCode

from .pxe import PXEBackend
from .memory import MemoryBackend

#** Variables **#
__all__ = ['CacheBackend']

#: default set of other backend sources to ignore
IGNORE = {MemoryBackend.source, PXEBackend.source}

#** Classes **#

@dataclass(slots=True)
class CacheRecord:
    """
    Record Entry for In-Memory Cache
    """
    message:    Message
    expiration: InitVar[int]
    expires:    float = field(init=False)
    accessed:   float = field(init=False)

    def __post_init__(self, expiration: int): #type: ignore
        """
        calculate expiration-time and last-accessed time
        """
        lease = self.message.options.get(IPLeaseTime)
        lease = lease.seconds if lease else 0
        ttl   = min(lease, expiration)
        now   = time.time()
        self.expires  = now + ttl
        self.accessed = now

    def is_expired(self) -> bool:
        """
        calculate if expiration has passed or ttl is expired
        """
        now = time.time()
        if self.expires <= now:
            return True
        elapsed = math.floor(now - self.accessed)
        if not elapsed:
            return False
        lease = self.message.options.get(IPLeaseTime)
        if lease:
            lease.seconds -= elapsed
            if lease.seconds <= 0:
                return True
        self.accessed = now
        return False

@dataclass(slots=True)
class CacheBackend(Backend):
    """
    In-Memory Cache Extension for Backend IP-Lease Results
    """
    source: ClassVar[str] = 'CACHE'

    backend: Backend
    expiration:     int      = 30
    maxsize:        int      = 10000
    ignore_sources: Set[str] = field(default_factory=lambda: IGNORE)
    logger:         Logger   = field(default_factory=lambda: getLogger('pydhcp'))

    mutex:       Lock                   = field(default_factory=Lock, init=False)
    cache:       Dict[str, CacheRecord] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.logger = self.logger.getChild('cache')

    def get_cache(self, hwaddr: bytes, mtype: MessageType) -> Optional[Answer]:
        """
        retrieve from cache directly if present
        """
        key = f'{hwaddr.hex()}->{mtype.value}'
        with self.mutex:
            if key not in self.cache:
                return
            record = self.cache[key]
            if record.is_expired():
                self.logger.debug(f'{key} expired')
                del self.cache[key]
                return
            return Answer(record.message, self.source)

    def set_cache(self, hwaddr: bytes, mtype: MessageType, answer: Answer):
        """
        save the given answers to cache for the specified domain/rtype
        """
        lease  = answer.message.options.get(IPLeaseTime)
        status = answer.message.options.get(DHCPStatusCode)
        if not lease \
            or answer.message.your_addr == ZeroIp \
            or status and status.value != StatusCode.Success:
            self.logger.debug(f'{hwaddr.hex()} skipping cache {mtype} {status}')
            return
        key = f'{hwaddr.hex()}->{mtype.value}'
        with self.mutex:
            if len(self.cache) >= self.maxsize:
                self.logger.debug(f'maxsize: {self.maxsize} exceeded. clearing cache!')
                self.cache.clear()
            self.cache[key] = CacheRecord(answer.message, self.expiration)

    def remove_cache(self, hwaddr: bytes, mtype: MessageType):
        """
        remove entry from cache (if it exists)
        """
        key = f'{hwaddr.hex()}->{mtype.value}'
        with self.mutex:
            self.cache.pop(key, None)

    def discover(self, address: Address, request: Message) -> Optional[Answer]:
        # attempt to retrieve from cache (if exists)
        mtype = cast(MessageType, request.message_type())
        answer = self.get_cache(request.client_hw, mtype)
        if answer is not None:
            return answer
        # complete standard lookup for answers (and cache if allowed)
        answer = self.backend.discover(address, request)
        if answer is None or answer.source in self.ignore_sources:
            return answer
        self.set_cache(request.client_hw, mtype, answer)
        return answer

    def request(self, address: Address, request: Message) -> Optional[Answer]:
        # attempt to retrieve from cache (if exists)
        mtype = cast(MessageType, request.message_type())
        answer = self.get_cache(request.client_hw, mtype)
        if answer is not None:
            return answer
        # complete standard lookup for answers (and cache if allowed)
        answer = self.backend.request(address, request)
        if answer is None or answer.source in self.ignore_sources:
            return answer
        self.set_cache(request.client_hw, mtype, answer)
        return answer

    def decline(self, address: Address, request: Message) -> Optional[Answer]:
        return self.backend.decline(address, request)

    def release(self, address: Address, request: Message) -> Optional[Answer]:
        return self.backend.release(address, request)
