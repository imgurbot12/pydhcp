"""
DHCP Assignment Cache Backend Extension
"""
from threading import Lock
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import NamedTuple, Optional, ClassVar, Set, Dict

from . import Assignment, Answer, Backend

#** Variables **#
__all__ = ['Cache']

#** Classes **#

class Record(NamedTuple):
    assign:     Assignment
    expiration: Optional[datetime]

@dataclass(repr=False)
class Cache(Backend):
    __slots__ = (
        'backend',
        'mutex',
        'cache'
    )

    source:     ClassVar[str] = 'Cache'
    backend:    Backend
    expiration: Optional[timedelta] = None
    maxsize:    Optional[int]       = None
    ignore:     Set[str]            = field(default_factory=set)

    def __post_init__(self):
        self.mutex = Lock()
        self.cache: Dict[bytes, Record] = {}

    def get_cache(self, key: bytes) -> Optional[Assignment]:
        """retrieve non-expired key from cache"""
        if key not in self.cache:
            return
        with self.mutex:
            record = self.cache[key]
            if record.expiration and record.expiration <= datetime.now():
                del self.cache[key]
                return
            return record.assign

    def set_cache(self, key: bytes, assign: Assignment):
        """save new assignment to cache"""
        with self.mutex:
            # clear cache until under max-size
            while self.maxsize and len(self.cache) >= self.maxsize:
                self.cache.popitem()
            # assign expiration
            expiration = None
            if self.expiration:
                expiration = datetime.now() + self.expiration
            self.cache[key] = Record(assign, expiration)

    def del_cache(self, key: bytes):
        """delete potential key from cache"""
        if key in self.cache:
            with self.mutex:
                self.cache.pop(key)

    def get_assignment(self, hwaddr: bytes) -> Answer:
        """
        Retrieve Assignment from Cache or Supplied Backend
        """
        # retrieve from cache
        assign = self.get_cache(hwaddr)
        if assign is not None:
            return Answer(assign, self.source)
        # retrieve from backup backend
        answer = self.backend.get_assignment(hwaddr)
        if answer.source not in self.ignore:
            self.set_cache(hwaddr, answer.assign)
        return answer
 
    def del_assignment(self, hwaddr: bytes):
        """
        Remove an Assignment tied to a particular HwAddress
        """
        self.del_cache(hwaddr)
        self.backend.del_assignment(hwaddr)
