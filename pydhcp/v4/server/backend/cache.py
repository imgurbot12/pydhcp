"""
Backend Extension to support In-Memory Answer Caching
"""
from copy import copy
from ipaddress import IPv4Address
from datetime import datetime, timedelta
from logging import Logger, getLogger
from threading import Lock
from typing import ClassVar, Dict, Optional, Set

from pyderive import InitVar, dataclass, field

from .memory import MemoryBackend, clean_mac
from .simple import SimpleAnswer, SimpleBackend

#** Variables **#
__all__ = ['CacheBackend']

#: default set of other backend sources to ignore
IGNORE = {MemoryBackend.source}

#** Classes **#

@dataclass(slots=True)
class CacheRecord:
    """
    Record Entry for In-Memory Cache
    """
    answer:    SimpleAnswer
    lifetime:  timedelta
    expires:   datetime = field(init=False)
    accessed:  datetime = field(init=False)

    def __post_init__(self):
        """
        calculate expiration-time and last-accessed time
        """
        lease = self.answer.lease
        ttl   = min(lease, self.lifetime)
        now   = datetime.now()
        self.expires  = now + ttl
        self.accessed = now

    def is_expired(self) -> bool:
        """
        calculate if expiration has passed or ttl is expired
        """
        now = datetime.now()
        if self.expires <= now:
            return True
        self.answer.lease -= now - self.accessed
        if self.answer.lease <= self.lifetime:
            return True
        self.accessed = now
        return False

@dataclass(slots=True)
class CacheBackend(SimpleBackend):
    """
    In-Memory Cache Extension for Backend IP-Lease Results
    """
    source: ClassVar[str] = 'CACHE'

    backend: SimpleBackend
    expiration:     timedelta = timedelta(seconds=30)
    maxsize:        int       = 10000
    ignore_sources: Set[str]  = field(default_factory=lambda: IGNORE)
    logger:         Logger    = field(default_factory=lambda: getLogger('pydhcp'))

    mutex:       Lock                   = field(default_factory=Lock, init=False)
    cache:       Dict[str, CacheRecord] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.logger = self.logger.getChild('cache')

    def get_cache(self, mac: str) -> Optional[SimpleAnswer]:
        """
        retrieve from cache directly if present

        :param mac: mac-address key linked to answer in cache
        :return:    ip-assignment answer stored in cache
        """
        mac = clean_mac(mac)
        with self.mutex:
            if mac not in self.cache:
                return
            record = self.cache[mac]
            if record.is_expired():
                self.logger.debug(f'{mac} expired')
                del self.cache[mac]
                return
            return record.answer

    def set_cache(self, mac: str, answer: SimpleAnswer):
        """
        save the given answers to cache for the specified mac-address

        :param mac:    mac-address key linked to answer
        :param answer: ip-assignment answer to store in cache
        """
        mac = clean_mac(mac)
        with self.mutex:
            if len(self.cache) >= self.maxsize:
                self.logger.debug(f'maxsize: {self.maxsize} exceeded. clearing cache!')
                self.cache.clear()
            answer        = copy(answer)
            answer.source = self.source
            self.cache[mac] = CacheRecord(answer, self.expiration)

    def request_address(self,
        mac: str, ipv4: Optional[IPv4Address]) -> Optional[SimpleAnswer]:
        answer = self.get_cache(mac)
        if answer and (ipv4 is None or answer.ipv4.ip == ipv4):
            return answer
        answer = self.backend.request_address(mac, ipv4)
        if answer and answer.source not in self.ignore_sources:
            self.set_cache(mac, answer)
        return answer

    def release_address(self, mac: str):
        return self.backend.release_address(mac)
