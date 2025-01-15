"""
"""
import time
import random
import logging
from datetime import timedelta
from ipaddress import IPv4Address, IPv4Network
from unittest import TestCase

from ..client import new_message_id
from ..message import Message
from ..options import *
from ..server.backend import Address, MemoryBackend
from ...enum import StatusCode

#** Variables **#
__all__ = ['MemoryTests']

ADDR   = Address('0.0.0.0', 67)
HWADDR = bytes.fromhex('aa:bb:cc:dd:ee:ff'.replace(':', ''))

#** Classes **#

class MemoryTests(TestCase):
    """
    Server Memory Backend Implementation UnitTests
    """

    def setUp(self):
        """
        setup memory backend for testing
        """
        self.dns     = IPv4Address('1.1.1.1')
        self.network = IPv4Network('192.168.1.0/29')
        self.gateway = IPv4Address('192.168.1.1')
        self.backend = MemoryBackend(
            network=self.network,
            dns=[self.dns],
            gateway=self.gateway,
            default_lease=timedelta(seconds=1)
        )
        self.backend.logger.setLevel(logging.CRITICAL)
        self.netmask = self.network.netmask

    def test_assign(self):
        """
        ensure memory backend preserves assignment betweeen discover/request
        """
        id     = new_message_id()
        offer  = IPv4Address('192.168.1.2')
        server = IPv4Address('0.0.0.0')
        # make initial DISCOVER request and recieve assignment
        with self.subTest('discover'):
            request  = Message.discover(id, HWADDR)
            response = self.backend.assign(ADDR, request)
            if response is None:
                return self.assertTrue(False, 'response is none')
            dns    = response.options.get(DomainNameServer)
            router = response.options.get(Router)
            subnet = response.options.get(SubnetMask)
            lease  = response.options.get(IPLeaseTime)
            self.assertEqual(response.id, request.id)
            self.assertEqual(response.your_addr, offer)
            self.assertEqual(dns, DomainNameServer([self.dns]))
            self.assertEqual(router, Router([self.gateway]))
            self.assertEqual(subnet, SubnetMask(self.netmask))
            self.assertEqual(lease, IPLeaseTime(1))
        # ensure assignment remains the same with REQUEST
        with self.subTest('request'):
            request  = Message.request(id, HWADDR, server, offer)
            response = self.backend.assign(ADDR, request)
            if response is None:
                return self.assertTrue(False, 'response is none')
            dns    = response.options.get(DomainNameServer)
            router = response.options.get(Router)
            subnet = response.options.get(SubnetMask)
            lease  = response.options.get(IPLeaseTime)
            self.assertEqual(response.id, request.id)
            self.assertEqual(response.your_addr, offer)
            self.assertEqual(dns, DomainNameServer([self.dns]))
            self.assertEqual(router, Router([self.gateway]))
            self.assertEqual(subnet, SubnetMask(self.netmask))
            self.assertEqual(lease, IPLeaseTime(1))

    def test_release(self):
        """
        ensure memory backend reuses addresses after release
        """
        id = new_message_id()
        self.test_assign()
        # make additional DISCOVER request for next address
        with self.subTest('request_1'):
            newhw = bytes([random.randint(0, 255) for _ in range(6)])
            request  = Message.discover(id, newhw)
            response = self.backend.assign(ADDR, request)
            self.assertEqual(response.id, request.id)
            self.assertEqual(response.your_addr, IPv4Address('192.168.1.3'))
        # release address and make DISCOVER address for same freed address
        with self.subTest('manual_release'):
            self.backend.reclaim_address(HWADDR.hex())
            request  = Message.discover(id, HWADDR)
            response = self.backend.assign(ADDR, request)
            self.assertEqual(response.id, request.id)
            self.assertEqual(response.your_addr, IPv4Address('192.168.1.2'))
        # make next DISCOVER request locking up an additional address
        with self.subTest('request_2'):
            newhw = bytes([random.randint(0, 255) for _ in range(6)])
            request  = Message.discover(id, newhw)
            response = self.backend.assign(ADDR, request)
            self.assertEqual(response.id, request.id)
            self.assertEqual(response.your_addr, IPv4Address('192.168.1.4'))
        # confirm automated release on lease expiration for addresses
        with self.subTest('auto_release'):
            time.sleep(1)
            self.backend.reclaim_all()
            request  = Message.discover(id, HWADDR)
            response = self.backend.assign(ADDR, request)
            self.assertEqual(response.id, request.id)
            self.assertEqual(response.your_addr, IPv4Address('192.168.1.2'))

    def test_exhaust(self):
        """
        ensure backend does not crash on ip-exhastion
        """
        for n in range(2, 7):
            id       = new_message_id()
            hwaddr   = bytes([random.randint(0, 255) for _ in range(6)])
            request  = Message.discover(id, hwaddr)
            response = self.backend.assign(ADDR, request)
            self.assertEqual(response.id, request.id)
            self.assertEqual(response.your_addr, IPv4Address(f'192.168.1.{n}'))
        id       = new_message_id()
        request  = Message.discover(id, HWADDR)
        response = self.backend.assign(ADDR, request)
        status   = response.options.get(DHCPStatusCode)
        self.assertEqual(response.id, request.id)
        self.assertEqual(response.your_addr, IPv4Address(f'0.0.0.0'))
        self.assertTrue(status is not None, 'status code should be set')
        self.assertEqual(status.value, StatusCode.NoAddrsAvail) #type: ignore
