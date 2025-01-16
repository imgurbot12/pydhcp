"""
Simplified DHCP Backend Protocol for IP-Assignments ONLY
"""
from abc import abstractmethod
from datetime import timedelta
from ipaddress import IPv4Address, IPv4Interface
from logging import Logger
from typing import ClassVar, List, Optional, Protocol

from pyderive import field
from pyderive.extensions.validate import BaseModel

from . import Address, Answer, Backend
from ... import *
from .... import HwType, StatusCode

#** Variables **#
__all__ = ['SimpleAnswer', 'SimpleBackend']

#** Classes **#

class SimpleAnswer(BaseModel):
    """
    Simplified Backend IP-Assignment Record
    """
    source:     str
    lease:      timedelta
    ipv4:       IPv4Interface
    routers:    List[IPv4Address]
    dns:        List[IPv4Address]
    dns_search: List[bytes] = field(default_factory=list)

class SimpleBackend(Backend, Protocol):
    """
    Simplified DHCP Backend for Simple IP-Assignment ONLY
    """
    source: ClassVar[str]
    logger: Logger

    @abstractmethod
    def request_address(self,
        mac: str, ipv4: Optional[IPv4Address]) -> Optional[SimpleAnswer]:
        """
        Retrieve IP-Address Assignment for Specified MAC-Address

        :param mac:  mac-address of dhcp client
        :param ipv4: requested ip-address of client (if specified)
        :return:     new network assignment (if granted)
        """
        raise NotImplementedError

    @abstractmethod
    def release_address(self, mac: str):
        """
        Release ANY existing Assignment for Specified MAC-Address

        :param mac: mac-address of dhcp client
        """
        raise NotImplementedError

    def _assign(self, address: Address, request: Message) -> Message:
        """
        retrieve assignment and generate dhcp response message

        :param address: client address
        :param request: dhcp request message
        :return:        dhcp response message
        """
        mac    = request.client_hw.hex()
        ipv4   = request.requested_address()
        assign = self.request_address(mac, ipv4)
        if assign is None:
            return request.reply([
                DHCPStatusCode(
                    value=StatusCode.NoAddrsAvail,
                    message=b'all addresses in use')])
        lease = int(assign.lease.total_seconds())
        self.logger.info(
            f'{address[0]} | {mac} -> ip={assign.ipv4} '
            f'gw={",".join(str(ip) for ip in assign.routers)} '
            f'dns={",".join(str(ip) for ip in assign.dns)} '
            f'lease={lease} source={assign.source}'
        )
        return request.reply(
            your_addr=assign.ipv4.ip,
            options=[
                DomainNameServer(assign.dns),
                DNSDomainSearchList(assign.dns_search),
                Router(assign.routers),
                SubnetMask(assign.ipv4.netmask),
                IPLeaseTime(lease),
                RenewalTime(int(lease * 0.5)), # 1/2 of lease time
                RebindTime(int(lease * 0.875)) # 7/8 of lease time
            ]
        )

    def discover(self, address: Address, request: Message) -> Optional[Answer]:
        if request.hw_type == HwType.Ethernet:
            message = self._assign(address, request)
            return Answer(message, self.source)

    def request(self, address: Address, request: Message) -> Optional[Answer]:
        if request.hw_type == HwType.Ethernet:
            message = self._assign(address, request)
            return Answer(message, self.source)

    def decline(self, address: Address, request: Message) -> Optional[Answer]:
        if request.hw_type == HwType.Ethernet:
            self.release_address(request.client_hw.hex())

    def release(self, address: Address, request: Message) -> Optional[Answer]:
        if request.hw_type == HwType.Ethernet:
            self.release_address(request.client_hw.hex())
