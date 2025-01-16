"""
DHCPv4 Simple UDP Client Implementation
"""
import socket
from datetime import timedelta
from ipaddress import IPv4Address
from random import randint
from typing import List, NamedTuple, Optional

from pyderive import dataclass

from .. import OpCode, Message, MessageType
from .. import DomainNameServer, DNSDomainSearchList, IPLeaseTime, Router

#** Variables **#
__all__ = ['Client', 'new_message_id']

#** Functions **#

def new_message_id() -> int:
    """
    generate a new valid id for a dns message packet

    :return: new valid message-id integer
    """
    return randint(1, 2 ** 32)

#** Classes **#

class IPAssignment(NamedTuple):
    """
    Simplified DHCP Option Results from DHCPv4 Server Ack
    """
    message:    Message
    lease:      timedelta
    ipv4:       IPv4Address
    subnet:     IPv4Address
    routers:    List[IPv4Address]
    dns:        List[IPv4Address]
    dns_search: List[bytes]

@dataclass(slots=True)
class Client:
    """
    Baseclass Socket-Based DNS Client Implementation
    """
    block_size: int = 65535
    timeout:    int = 10
    interface:  Optional[str] = None

    def request(self, request: Message) -> Message:
        """
        make dhcp request and wait for server response

        :param request: dhcp request message
        :return:        dhcp response message
        """
        if request.op != OpCode.BootRequest:
            raise ValueError('Message is not DHCP Request')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if self.interface:
            iface = self.interface.encode()
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, iface)
        sock.settimeout(self.timeout)
        try:
            sock.bind(('', 68))
            sock.sendto(request.pack(), ('255.255.255.255', 67))
            while True:
                data, _  = sock.recvfrom(self.block_size)
                response = Message.unpack(data)
                if response.id == request.id \
                    and response.op == OpCode.BootReply:
                    return response
        finally:
            sock.close()

    def request_assignment(self, mac: str):
        """
        complete traditional dhcp round-robin request for ip-address

        :param mac: mac-address linked to network interface
        :return:    ip-assignment recieved from dhcp-server
        """
        # make initial discover request
        id       = new_message_id()
        hwaddr   = bytes.fromhex(mac.replace(':', '').replace('-', ''))
        request  = Message.discover(id, hwaddr)
        response = self.request(request)
        if not response.your_addr \
            or response.message_type() != MessageType.Offer:
            raise RuntimeError('DHCP Failed to Offer IPAddress')
        # make request for specified ip-address
        request  = Message.request(id, hwaddr,  response.your_addr)
        response = self.request(request)
        if not response.your_addr \
            or response.message_type() != MessageType.Ack:
            raise RuntimeError('DHCP Failed to Acknowledge Request')
        # return new assignment
        subnet  = response.subnet_mask()
        routers = response.options.get(Router)
        dns     = response.options.get(DomainNameServer)
        search  = response.options.get(DNSDomainSearchList)
        lease   = response.options.get(IPLeaseTime)
        if subnet is None:
            raise RuntimeError('Subnet Not Specified')
        if routers is None:
            raise RuntimeError('No Routing Gateways Specified')
        if lease is None:
            raise RuntimeError('IP Lease Not Specified')
        return IPAssignment(
            message=response,
            ipv4=response.your_addr,
            lease=timedelta(seconds=lease.seconds),
            subnet=subnet,
            routers=routers.ips,
            dns=dns.ips if dns else [],
            dns_search=search.domains if search else []
        )

