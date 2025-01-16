"""
Example Memory Based Backend for DHCP Server
"""
from datetime import datetime, timedelta
from ipaddress import IPv4Address, IPv4Interface, IPv4Network
from logging import Logger, getLogger
from threading import Lock
from typing import ClassVar, Dict, Iterator, List, Optional

from pyderive import dataclass
from pyderive.extensions.serde import field
from pyderive.extensions.validate import BaseModel

from .simple import SimpleAnswer, SimpleBackend

#** Variables **#
__all__ = ['MemoryBackend']

#: default lease assignment for dhcp memory-backend
DEFAULT_LEASE = timedelta(seconds=3600)

#** Functions **#

def clean_mac(mac: str) -> str:
    """
    clean mac-address for use as a standardized key

    :param mac: mac-address to clean
    :return:    cleaned mac-address
    """
    return mac.lower().replace(':', '').replace('-', '')

#** Classes **#

class IPRecord(BaseModel):
    """
    Individual IP-Assignment Record
    """
    ipv4:    IPv4Interface               = field(aliases=['ip'])
    dns:     Optional[List[IPv4Address]] = None
    search:  Optional[List[bytes]]       = None
    lease:   Optional[timedelta]         = None
    gateway: Optional[IPv4Address]       = field(default=None, aliases=['gw'])

class Record(BaseModel):
    """
    Tempory IPRecord with Expiration
    """
    record:  IPRecord
    expires: datetime

@dataclass(slots=True)
class MemoryBackend(SimpleBackend):
    """
    Simple In-Memory DHCP Server Data/Address Backend
    """
    source: ClassVar[str] = 'MEMORY'

    network:       IPv4Network
    gateway:       IPv4Address
    dns:           List[IPv4Address]
    dns_search:    List[bytes] = field(default_factory=list)
    default_lease: timedelta   = field(default_factory=lambda: DEFAULT_LEASE)
    logger:        Logger      = field(default_factory=lambda: getLogger('pydhcp'))

    static:  Dict[str, IPRecord] = field(init=False, default_factory=dict)
    records: Dict[str, Record]   = field(init=False, default_factory=dict)
    lock:    Lock                = field(init=False, default_factory=Lock)

    addresses: Iterator[IPv4Address] = field(init=False)
    reclaimed: List[IPv4Interface]   = field(init=False, default_factory=list)

    def __post_init__(self):
        self.addresses = self.network.hosts()

    def set_static(self, mac: str, ipaddr: IPv4Address, **settings):
        """
        assign static address within configured dhcp network

        :param mac:      mac-address assigned to dhcp
        :param ipaddr:   ip-address to staticly assign to mac
        :param settings: additional settings for static assignment
        """
        if ipaddr not in self.network:
            raise ValueError(f'{ipaddr} not within {self.network}')
        mac  = clean_mac(mac)
        ipv4 = IPv4Interface(f'{ipaddr}/{self.network.netmask}')
        self.static[mac] = IPRecord(ipv4, **settings)

    def _reclaim_all(self):
        """
        reclaim addresses from expired dhcp leases
        """
        now   = datetime.now()
        clean = [mac for mac, r in self.records.items() if r.expires <= now]
        for mac in clean:
            record = self.records.pop(mac)
            self.reclaimed.append(record.record.ipv4)
        self.reclaimed.sort()

    def _reclaim_address(self, mac: str):
        """
        reclaim single address for database address-pool

        :param mac: mac-address
        """
        record = self.records.pop(mac, None)
        if record is not None:
            self.reclaimed.append(record.record.ipv4)

    def _next_ip(self,
        mac: str, ipv4: Optional[IPv4Address]) -> Optional[IPv4Interface]:
        """
        retrieve ip-assignment based on dhcp request and database

        :param request: dhcp request message
        :return:        ip-address assignment (if address available)
        """
        # check if client has existing assignment
        now    = datetime.now()
        record = self.records.get(mac)
        if record is not None and record.expires >= now:
            # extend existing lease and return (if exists)
            lease          = record.record.lease or self.default_lease
            record.expires = now + lease
            return record.record.ipv4
        # check if requested-ip is available
        if ipv4 is not None:
            addr = IPv4Interface(f'{ipv4}/{self.network.netmask}')
            if addr in self.reclaimed:
                self.reclaimed.remove(addr)
                return addr
        # retrieve first available in reclaimed or next in hostlist
        if self.reclaimed:
            return self.reclaimed.pop(0)
        # retrieve next ip in host-list (skipping reserved ips)
        try:
            ipaddr    = None
            reserved  = {r.ipv4.ip for r in self.static.values()}
            reserved |= set([self.gateway, *self.dns])
            while ipaddr is None or ipaddr in reserved:
                ipaddr = next(self.addresses)
            return IPv4Interface(f'{ipaddr}/{self.network.netmask}')
        except StopIteration:
            return

    def request_address(self,
        mac: str, ipv4: Optional[IPv4Address]) -> Optional[SimpleAnswer]:
        with self.lock:
            self._reclaim_all()
            # retrieve assignment from static or retirve available ip-address
            record = self.static.get(mac)
            if record is None:
                address = self._next_ip(mac, ipv4)
                record  = IPRecord(address) if address else record
            if record is None:
                return
            # assign record to database and return assignment
            lease = record.lease or self.default_lease
            self.records[mac] = Record(record, datetime.now() + lease)
            return SimpleAnswer(
                source=self.source,
                lease=lease,
                ipv4=record.ipv4,
                routers=[record.gateway or self.gateway],
                dns=record.dns or self.dns,
                dns_search=record.search or self.dns_search,
            )

    def release_address(self, mac: str):
        with self.lock:
            self._reclaim_address(mac)
            self._reclaim_all()
