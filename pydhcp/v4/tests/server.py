"""
DHCPv4 Server In-Memory Backend UnitTests
"""
import asyncio
import random
from datetime import timedelta
from ipaddress import IPv4Address, IPv4Network
from typing import cast
from unittest import IsolatedAsyncioTestCase

from .. import *

from ..server.backend import Address, MemoryBackend, SimpleAnswer

#** Variables **#
__all__ = ['MemoryTests']

ADDR   = Address('0.0.0.0', 67)
HWADDR = 'aa:bb:cc:dd:ee:ff'.replace(':', '')

#** Classes **#

class MemoryTests(IsolatedAsyncioTestCase):
    """
    Server Memory Backend Implementation UnitTests
    """

    def setUp(self):
        """
        Set-up memory backend for testing
        """
        self.dns     = IPv4Address('1.1.1.1')
        self.network = IPv4Network('192.168.1.0/29')
        self.gateway = IPv4Address('192.168.1.1')
        self.backend = MemoryBackend(
            network=self.network,
            dns=[self.dns],
            gateway=self.gateway,
            default_lease=timedelta(milliseconds=100)
        )
        self.netmask = self.network.netmask

    async def test_assign(self):
        """
        Ensure memory backend preserves assignment between discover/request
        """
        for n in range(2):
            with self.subTest('request_address', n=n):
                answer = await self.backend.request_address(HWADDR, None)
                if answer is None:
                    return self.assertTrue(False, 'response is none')
                self.assertEqual(answer.ipv4.ip, IPv4Address('192.168.1.2'))
                self.assertEqual(answer.lease, timedelta(milliseconds=100))
                self.assertEqual(answer.ipv4.netmask, self.netmask)
                self.assertListEqual(answer.dns, [self.dns])
                self.assertListEqual(answer.routers, [self.gateway])

    async def test_release(self):
        """
        Ensure memory backend reuses addresses after release
        """
        await self.test_assign()
        with self.subTest('get_next_address'):
            newhw = bytes([random.randint(0, 255) for _ in range(6)])
            answer = await self.backend.request_address(newhw.hex(), None)
            if answer is None:
                return self.assertTrue(False, 'response is none')
            self.assertEqual(answer.ipv4.ip, IPv4Address('192.168.1.3'))
        with self.subTest('manual_release_and_renew'):
            await self.backend.release_address(HWADDR)
            answer = await self.backend.request_address(HWADDR, None)
            if answer is None:
                return self.assertTrue(False, 'response is none')
            self.assertEqual(answer.ipv4.ip, IPv4Address('192.168.1.2'))
        with self.subTest('get_next_address_2'):
            newhw = bytes([random.randint(0, 255) for _ in range(6)])
            answer = await self.backend.request_address(newhw.hex(), None)
            if answer is None:
                return self.assertTrue(False, 'response is none')
            self.assertEqual(answer.ipv4.ip, IPv4Address('192.168.1.4'))
        with self.subTest('auto_release_and_renew'):
            await asyncio.sleep(0.1)
            answer = await self.backend.request_address(HWADDR, None)
            if answer is None:
                return self.assertTrue(False, 'response is none')
            self.assertEqual(answer.ipv4.ip, IPv4Address('192.168.1.2'))

    async def test_static(self):
        """
        Test static assignment override
        """
        static = IPv4Address('192.168.1.3')
        self.backend.set_static(HWADDR, static)
        answer = await self.backend.request_address(HWADDR, None)
        if answer is None:
            return self.assertTrue(False, 'response is none')
        self.assertEqual(answer.ipv4.ip, static)

    async def test_exhaust(self):
        """
        Ensure backend does not crash on ip exhaustion
        """
        for n in range(2, 7):
            newhw  = bytes([random.randint(0, 255) for _ in range(6)])
            answer = await self.backend.request_address(newhw.hex(), None)
            self.assertIsNotNone(answer)
            answer = cast(SimpleAnswer, answer)
            self.assertEqual(answer.ipv4.ip, IPv4Address(f'192.168.1.{n}'))
        answer = await self.backend.request_address(HWADDR, None)
        self.assertIsNone(answer, 'addresses should be exhausted')
