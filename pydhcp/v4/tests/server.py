"""
DHCPv4 Server In-Memory Backend UnitTests
"""
import time
import random
from datetime import timedelta
from ipaddress import IPv4Address, IPv4Network
from unittest import TestCase

from .. import *

from ..server.backend import Address, MemoryBackend

#** Variables **#
__all__ = ['MemoryTests']

ADDR   = Address('0.0.0.0', 67)
HWADDR = 'aa:bb:cc:dd:ee:ff'.replace(':', '')

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
        self.netmask = self.network.netmask

    def test_assign(self):
        """
        ensure memory backend preserves assignment betweeen discover/request
        """
        for n in range(2):
            with self.subTest('request_address', n=n):
                answer = self.backend.request_address(HWADDR, None)
                if answer is None:
                    return self.assertTrue(False, 'response is none')
                self.assertEqual(answer.ipv4.ip, IPv4Address('192.168.1.2'))
                self.assertEqual(answer.lease, timedelta(seconds=1))
                self.assertEqual(answer.ipv4.netmask, self.netmask)
                self.assertListEqual(answer.dns, [self.dns])
                self.assertListEqual(answer.routers, [self.gateway])

    def test_release(self):
        """
        ensure memory backend reuses addresses after release
        """
        self.test_assign()
        with self.subTest('get_next_address'):
            newhw = bytes([random.randint(0, 255) for _ in range(6)])
            answer = self.backend.request_address(newhw.hex(), None)
            if answer is None:
                return self.assertTrue(False, 'response is none')
            self.assertEqual(answer.ipv4.ip, IPv4Address('192.168.1.3'))
        with self.subTest('manual_release_and_renew'):
            self.backend.release_address(HWADDR)
            answer = self.backend.request_address(HWADDR, None)
            if answer is None:
                return self.assertTrue(False, 'response is none')
            self.assertEqual(answer.ipv4.ip, IPv4Address('192.168.1.2'))
        with self.subTest('get_next_address_2'):
            newhw = bytes([random.randint(0, 255) for _ in range(6)])
            answer = self.backend.request_address(newhw.hex(), None)
            if answer is None:
                return self.assertTrue(False, 'response is none')
            self.assertEqual(answer.ipv4.ip, IPv4Address('192.168.1.4'))
        with self.subTest('auto_release_and_renew'):
            time.sleep(1)
            self.backend._reclaim_all()
            answer = self.backend.request_address(HWADDR, None)
            if answer is None:
                return self.assertTrue(False, 'response is none')
            self.assertEqual(answer.ipv4.ip, IPv4Address('192.168.1.2'))

    def test_static(self):
        """
        test static assignment override
        """
        static = IPv4Address('192.168.1.3')
        self.backend.set_static(HWADDR, static)
        answer = self.backend.request_address(HWADDR, None)
        if answer is None:
            return self.assertTrue(False, 'response is none')
        self.assertEqual(answer.ipv4.ip, static)

    def test_exhaust(self):
        """
        ensure backend does not crash on ip-exhastion
        """
        for n in range(2, 7):
            newhw  = bytes([random.randint(0, 255) for _ in range(6)])
            answer = self.backend.request_address(newhw.hex(), None)
            if answer is None:
                return self.assertTrue(False, 'response is none')
            self.assertEqual(answer.ipv4.ip, IPv4Address(f'192.168.1.{n}'))
        answer = self.backend.request_address(HWADDR, None)
        self.assertIsNone(answer, 'addresses should be exhausted')
