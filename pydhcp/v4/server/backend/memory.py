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

from . import Address, Answer, Backend
from ...message import Message
from ...options import *
from ....enum import StatusCode

#** Variables **#
__all__ = ['MemoryRecord', 'MemoryBackend']

#: default lease assignment for dhcp memory-backend
DEFAULT_LEASE = timedelta(seconds=3600)

#** Classees **#

class MemoryRecord(BaseModel):
    """
    Individual IP-Assignment Record
    """
    ipaddr:  IPv4Interface               = field(aliases=['ip'])
    dns:     Optional[List[IPv4Address]] = None
    lease:   Optional[timedelta]         = None
    gateway: Optional[IPv4Address]       = field(default=None, aliases=['gw'])

class Record(BaseModel):
    record:  MemoryRecord
    expires: datetime

@dataclass(slots=True)
class MemoryBackend(Backend):
    """
    Simple In-Memory DHCP Server Data/Address Backend
    """
    source: ClassVar[str] = 'MEMORY'

    network:       IPv4Network
    dns:           List[IPv4Address]
    gateway:       IPv4Address
    default_lease: timedelta = field(default_factory=lambda: DEFAULT_LEASE)
    logger:        Logger    = field(default_factory=lambda: getLogger('pydhcp'))

    static:  Dict[str, MemoryRecord] = field(default_factory=dict)
    records: Dict[str, Record]       = field(init=False, default_factory=dict)
    lock:    Lock                    = field(init=False, default_factory=Lock)

    addresses: Iterator[IPv4Address] = field(init=False)
    reclaimed: List[IPv4Interface]   = field(init=False, default_factory=list)

    def __post_init__(self):
        self.addresses = self.network.hosts()

    def reclaim_all(self):
        """
        reclaim addresses from expired dhcp leases
        """
        now   = datetime.now()
        clean = [hw for hw, r in self.records.items() if r.expires <= now]
        for hwaddr in clean:
            record = self.records.pop(hwaddr)
            self.reclaimed.append(record.record.ipaddr)
        self.reclaimed.sort()

    def reclaim_address(self, hwaddr: str):
        """
        reclaim single address for database address-pool

        :param hwaddr: stringified hardware-address (mac)
        """
        record = self.records.pop(hwaddr, None)
        if record is not None:
            self.reclaimed.append(record.record.ipaddr)

    def next_ip(self, request: Message) -> Optional[IPv4Interface]:
        """
        retrieve ip-assignment based on dhcp request and database

        :param request: dhcp request message
        :return:        ip-address assignment (if address available)
        """
        # check if client has existing assignment
        now    = datetime.now()
        hwaddr = request.client_hw.hex()
        record = self.records.get(hwaddr)
        if record is not None and record.expires >= now:
            # extend existing lease and return (if exists)
            lease          = record.record.lease or self.default_lease
            record.expires = now + lease
            return record.record.ipaddr
        # check if requested-ip is available
        req_ip = request.requested_address()
        if req_ip is not None:
            addr = IPv4Interface(f'{req_ip}/{self.network.netmask}')
            if addr in self.reclaimed:
                self.reclaimed.remove(addr)
                return addr
        # retrieve first available in reclaimed or next in hostlist
        if self.reclaimed:
            return self.reclaimed.pop(0)
        # retrieve next ip in host-list (skipping reserved gateway)
        try:
            ipaddr = None
            while ipaddr is None or ipaddr == self.gateway:
                ipaddr = next(self.addresses)
            return IPv4Interface(f'{ipaddr}/{self.network.netmask}')
        except StopIteration:
            return

    def assign(self, address: Address, request: Message) -> Message:
        """
        assign new address from available pool to requestee

        :param address: client address
        :param request: dhcp request message
        :return:        dhcp response message (if address is available)
        """
        addr   = f'{address[0]}:{address[1]}'
        hwaddr = request.client_hw.hex()
        # get next ip-address available
        ipaddr = self.next_ip(request)
        if ipaddr is None:
            self.logger.error(f'{addr} | network out of ip addresses!')
            return request.reply([
                DHCPStatusCode(StatusCode.NoAddrsAvail, b'all addresses in use')
            ])
        # build reply with dns/subnet/gateway assignments
        record   = self.static.get(hwaddr) or MemoryRecord(ipaddr)
        lease    = record.lease or self.default_lease
        response = request.reply(
            your_addr=ipaddr.ip,
            options=[
                DomainNameServer(record.dns or self.dns),
                Router([record.gateway or self.gateway]),
                SubnetMask(ipaddr.netmask),
                IPLeaseTime(int(lease.total_seconds()))
            ]
        )
        # assign to memory database and return
        self.records[hwaddr] = Record(record, datetime.now() + lease)
        return response

    def discover(self, address: Address, request: Message) -> Optional[Answer]:
        with self.lock:
            self.reclaim_all()
            message = self.assign(address, request)
            return Answer(message, self.source)

    def request(self, address: Address, request: Message) -> Optional[Answer]:
        with self.lock:
            self.reclaim_all()
            message = self.assign(address, request)
            return Answer(message, self.source)

    def decline(self, address: Address, request: Message) -> Optional[Answer]:
        with self.lock:
            self.reclaim_all()
            self.reclaim_address(request.client_hw.hex())

    def release(self, address: Address, request: Message) -> Optional[Answer]:
        with self.lock:
            self.reclaim_all()
            self.reclaim_address(request.client_hw.hex())
