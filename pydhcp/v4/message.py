"""
DHCPv4 Message Object Implementation
"""
from ipaddress import IPv4Address
from typing import List, Optional, Sequence, Union, cast
from typing_extensions import Annotated, Self

from pyderive import dataclass
from pystructs import U16, U32, U8, Const, Context, IPv4, StaticBytes, Struct

from ..abc import OptionList
from ..enum import HwType
from .enum import MessageType, OpCode, OptionCode
from .options import *

#** Variables **#
__all__ = ['ZeroIp', 'Message']

#: pre-converted default ip-address for dhcpv4 packet
ZeroIp = IPv4Address('0.0.0.0')

#: magic cookie to include in DHCP message
MAGIC_COOKIE = bytes((0x63, 0x82, 0x53, 0x63))

OptionListv4 = OptionList[Option]
OptionParam  = Union[OptionListv4, Sequence[Option], None]

#** Classes **#

class HexBytes(bytes):
    def __repr__(self) -> str:
        return f'0x{self.hex()}'

class MessageHeader(Struct):
    opcode:       Annotated[OpCode, U8]
    hw_type:      Annotated[HwType, U8]
    hw_length:    U8
    hops:         U8
    message_id:   U32
    seconds:      U16
    flags:        U16
    client_addr:  IPv4
    your_addr:    IPv4
    server_addr:  IPv4
    gateway_addr: IPv4
    hw_addr:      Annotated[HexBytes, StaticBytes(16)]
    server_name:  Annotated[bytes, StaticBytes(64)]
    boot_file:    Annotated[bytes, StaticBytes(128)]
    magic_cookie: Annotated[bytes, Const(MAGIC_COOKIE)] = MAGIC_COOKIE

@dataclass(slots=True)
class Message:
    """
    DHCP Message Object Definition (Request & Response Packet)
    """
    op:           OpCode
    id:           int
    client_hw:    bytes
    options:      OptionListv4
    hw_type:      HwType      = HwType.Ethernet
    hops:         int         = 0
    seconds:      int         = 0
    flags:        int         = 0
    client_addr:  IPv4Address = ZeroIp
    your_addr:    IPv4Address = ZeroIp
    server_addr:  IPv4Address = ZeroIp
    gateway_addr: IPv4Address = ZeroIp
    server_name:  bytes       = b''
    boot_file:    bytes       = b''

    def message_type(self) -> Optional[MessageType]:
        """
        retrieve `MessageType` option value from options (if present)

        :return: assigned packet message-type
        """
        option = self.options.get(DHCPMessageType)
        return option.mtype if option else None

    def requested_options(self) -> List[OptionCode]:
        """
        retrieve `ParamRequestList` option value from options (if present)

        :return: list of requested option-codes
        """
        option = self.options.get(ParamRequestList)
        return option.params if option else []

    def requested_address(self) -> Optional[IPv4Address]:
        """
        retrieve `RequestedIPAddr` option value from options (if present)

        :return: client requested ipv4 address
        """
        option = self.options.get(RequestedIPAddr)
        return option.ip if option else None

    def subnet_mask(self) -> Optional[IPv4Address]:
        """
        retrieve `SubnetMask` option value from options (if present)
        """
        option = self.options.get(SubnetMask)
        return option.mask if option else None

    def broadcast_address(self) -> Optional[IPv4Address]:
        """
        retrieve `BroadcastAddr` option value from options (if present)
        """
        option = self.options.get(BroadcastAddr)
        return option.addr if option else None

    def server_identifier(self) -> Optional[IPv4Address]:
        """
        retrieve `ServerIdentifier` option value from options (if present)
        """
        option = self.options.get(ServerIdentifier)
        return option.ip if option else None

    @classmethod
    def discover(cls,
        id:      int,
        hwaddr:  bytes,
        ipaddr:  Optional[IPv4Address] = None,
        options: OptionParam           = None,
        **kwargs,
    ) -> 'Message':
        """
        DHCP DISCOVER Message Constructor

        :param id:      transaction-id
        :param hwaddr:  client hardware address
        :param ipaddr:  requested dhcp ip-address
        :param options: additional message options
        :param kwargs:  additional message kwargs
        :return:        new dhcp discover message
        """
        ops: Sequence[Option] = options or []
        message = Message(
            op=OpCode.BootRequest,
            id=id,
            client_hw=hwaddr,
            options=OptionList([
                DHCPMessageType(MessageType.Discover),
                ParamRequestList([
                    OptionCode.SubnetMask,
                    OptionCode.BroadcastAddress,
                    OptionCode.TimeOffset,
                    OptionCode.Router,
                    OptionCode.DomainName,
                    OptionCode.DomainNameServer,
                    OptionCode.HostName,
                ]),
                *ops
            ]),
            **kwargs
        )
        if ipaddr is not None:
            message.options.insert(1, RequestedIPAddr(ipaddr))
        return message

    @classmethod
    def request(cls,
        id:      int,
        hwaddr:  bytes,
        ipaddr:  IPv4Address,
        options: OptionParam = None,
        **kwargs,
    ) -> 'Message':
        """
        DHCP REQUEST Message Constructor

        :param id:      transaction-id
        :param hwaddr:  client hardware address
        :param server:  dhcp server address for request
        :param ipaddr:  requested dhcp ip-address
        :param options: additional message options
        :param kwargs:  additional message kwargs
        :return:        new dhcp request message
        """
        ops: Sequence[Option] = options or []
        return Message(
            op=OpCode.BootRequest,
            id=id,
            client_hw=hwaddr,
            options=OptionList([
                DHCPMessageType(MessageType.Request),
                RequestedIPAddr(ipaddr),
                ParamRequestList([
                    OptionCode.SubnetMask,
                    OptionCode.BroadcastAddress,
                    OptionCode.TimeOffset,
                    OptionCode.Router,
                    OptionCode.DomainName,
                    OptionCode.DomainNameServer,
                    OptionCode.HostName,
                ]),
                *ops,
            ]),
            **kwargs,
        )

    def reply(self, options: OptionParam = None, **kwargs) -> 'Message':
        """
        generate template `BootReply` Message for current Message request

        :param options: options to pass into generated message
        :param kwargs:  additional settings for message generation
        :return:        new generated message reply object
        """
        ops: OptionListv4 = OptionList(options or [])
        return Message(
            op=OpCode.BootReply,
            id=self.id,
            client_hw=self.client_hw,
            hw_type=self.hw_type,
            options=ops,
            **kwargs
        )

    def pack(self, ctx: Optional[Context] = None) -> bytes:
        """
        pack message object into serialized bytes

        :param ctx: serialization context object
        :return:    serialized bytes
        """
        ctx   = ctx or Context()
        data  = bytearray()
        data += MessageHeader(
            opcode=self.op,
            hw_type=self.hw_type,
            hw_length=len(self.client_hw),
            hops=self.hops,
            message_id=self.id,
            seconds=self.seconds,
            flags=self.flags,
            client_addr=self.client_addr,
            your_addr=self.your_addr,
            server_addr=self.server_addr,
            gateway_addr=self.gateway_addr,
            hw_addr=cast(HexBytes, self.client_hw),
            server_name=self.server_name,
            boot_file=self.boot_file,
        ).pack(ctx)
        data += b''.join(pack_option(op, ctx) for op in self.options)
        if not any(op.opcode == OptionCode.End for op in self.options):
            data += bytes((OptionCode.End, ))
        return bytes(data)

    @classmethod
    def unpack(cls, raw: bytes, ctx: Optional[Context] = None) -> Self:
        """
        unpack serialized bytes into deserialized message object

        :param raw: raw byte buffer
        :param ctx: deserialization context object
        :return:    unpacked message object
        """
        ctx     = ctx or Context()
        header  = MessageHeader.unpack(raw, ctx)
        options = []
        while raw[ctx.index] not in (0, OptionCode.End):
            option = unpack_option(raw, ctx)
            options.append(option)
        return cls(
            op=header.opcode,
            id=header.message_id,
            client_hw=header.hw_addr,
            options=OptionList(options),
            hw_type=header.hw_type,
            hops=header.hops,
            seconds=header.seconds,
            flags=header.flags,
            client_addr=header.client_addr,
            your_addr=header.your_addr,
            gateway_addr=header.gateway_addr,
            server_name=header.server_name,
            boot_file=header.boot_file,
        )
