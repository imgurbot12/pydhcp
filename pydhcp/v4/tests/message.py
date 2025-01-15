"""
DHCP Message Packet Parsing UnitTests
"""
from ipaddress import IPv4Address
from unittest import TestCase

from .. import *

#** Variables **#
__all__ = ['MessageTests']

DHCP_DISCOVER = '0101060000003d1d000000000000000000000000000000000000000000' +\
    '0b8201fc42000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000638253' +\
    '633501013d0701000b8201fc4232040000000037040103062aff00000000000000'

DHCP_OFFER = '0201060000003d1d0000000000000000c0a8000ac0a8000100000000000b8' +\
    '201fc42000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000638253633' +\
    '501020104ffffff003a04000007083b0400000c4e330400000e103604c0a80001ff000' +\
    '0000000000000000000000000000000000000000000000000'

DHCP_REQUEST = '0101060000003d1e0000000000000000000000000000000000000000000' +\
    'b8201fc420000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000006382536' +\
    '33501033d0701000b8201fc423204c0a8000a3604c0a8000137040103062aff00'

DHCP_ACK = '0201060000003d1e0000000000000000c0a8000a0000000000000000000b820' +\
    '1fc4200000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000063825363350' +\
    '1053a04000007083b0400000c4e330400000e103604c0a800010104ffffff00ff00000' +\
    '00000000000000000000000000000000000000000000000'

#** Classes **#

class MessageTests(TestCase):
    """
    DHCP Packet Parsing UnitTests
    """

    def test_discover(self):
        """
        ensure dhcp discover message parses properly
        """
        data    = bytes.fromhex(DHCP_DISCOVER)
        message = Message.unpack(data)
        self.assertEqual(message.op, OpCode.BootRequest)
        self.assertEqual(message.id, 15645)
        self.assertEqual(message.client_hw, bytes.fromhex('000b8201fc42'))
        self.assertEqual(len(message.options), 4)
        self.assertEqual(message.hops, 0)
        self.assertEqual(message.seconds, 0)
        self.assertEqual(message.flags, 0)
        self.assertEqual(message.client_addr, ZeroIp)
        self.assertEqual(message.your_addr, ZeroIp)
        self.assertEqual(message.server_addr, ZeroIp)
        self.assertEqual(message.gateway_addr, ZeroIp)
        self.assertEqual(message.server_name, b'')
        self.assertEqual(message.boot_file, b'')
        self.assertEqual(message.message_type(), MessageType.Discover)
        self.assertEqual(message.requested_address(), ZeroIp)

    def test_offer(self):
        """
        ensure dhcp offer message parses properly
        """
        data    = bytes.fromhex(DHCP_OFFER)
        message = Message.unpack(data)
        self.assertEqual(message.op, OpCode.BootReply)
        self.assertEqual(message.id, 15645)
        self.assertEqual(message.client_hw, bytes.fromhex('000b8201fc42'))
        self.assertEqual(len(message.options), 6)
        self.assertEqual(message.hops, 0)
        self.assertEqual(message.seconds, 0)
        self.assertEqual(message.flags, 0)
        self.assertEqual(message.client_addr, ZeroIp)
        self.assertEqual(message.your_addr, IPv4Address('192.168.0.10'))
        self.assertEqual(message.server_addr, ZeroIp)
        self.assertEqual(message.gateway_addr, ZeroIp)
        self.assertEqual(message.server_name, b'')
        self.assertEqual(message.boot_file, b'')
        self.assertEqual(message.message_type(), MessageType.Offer)
        self.assertEqual(message.subnet_mask(), IPv4Address('255.255.255.0'))
        self.assertEqual(message.server_identifier(), IPv4Address('192.168.0.1'))

    def test_request(self):
        """
        ensure dhcp request message parses properly
        """
        data    = bytes.fromhex(DHCP_REQUEST)
        message = Message.unpack(data)
        self.assertEqual(message.op, OpCode.BootRequest)
        self.assertEqual(message.id, 15646)
        self.assertEqual(message.client_hw, bytes.fromhex('000b8201fc42'))
        self.assertEqual(len(message.options), 5)
        self.assertEqual(message.hops, 0)
        self.assertEqual(message.seconds, 0)
        self.assertEqual(message.flags, 0)
        self.assertEqual(message.client_addr, ZeroIp)
        self.assertEqual(message.your_addr, ZeroIp)
        self.assertEqual(message.server_addr, ZeroIp)
        self.assertEqual(message.gateway_addr, ZeroIp)
        self.assertEqual(message.server_name, b'')
        self.assertEqual(message.boot_file, b'')
        self.assertEqual(message.message_type(), MessageType.Request)
        self.assertEqual(message.requested_address(), IPv4Address('192.168.0.10'))
        self.assertEqual(message.server_identifier(), IPv4Address('192.168.0.1'))

    def test_ack(self):
        """
        ensure dhcp ack message parses properly
        """
        data    = bytes.fromhex(DHCP_ACK)
        message = Message.unpack(data)
        self.assertEqual(message.op, OpCode.BootReply)
        self.assertEqual(message.id, 15646)
        self.assertEqual(message.client_hw, bytes.fromhex('000b8201fc42'))
        self.assertEqual(len(message.options), 6)
        self.assertEqual(message.hops, 0)
        self.assertEqual(message.seconds, 0)
        self.assertEqual(message.flags, 0)
        self.assertEqual(message.client_addr, ZeroIp)
        self.assertEqual(message.your_addr, IPv4Address('192.168.0.10'))
        self.assertEqual(message.server_addr, ZeroIp)
        self.assertEqual(message.gateway_addr, ZeroIp)
        self.assertEqual(message.server_name, b'')
        self.assertEqual(message.boot_file, b'')
        self.assertEqual(message.message_type(), MessageType.Ack)
        self.assertEqual(message.subnet_mask(), IPv4Address('255.255.255.0'))
        self.assertEqual(message.server_identifier(), IPv4Address('192.168.0.1'))


