"""
SimpleSession Handler Implentations
"""
from copy import copy
from enum import IntEnum
from functools import wraps
from datetime import datetime, timedelta
from ipaddress import IPv4Address, IPv4Interface
from typing import *
from threading import Lock

from pyderive import dataclass, field

from .server import HandlerFunc, Context
from ..message import Message, OptionCode
from ..options import *
from ...enum import Arch

#** Variables **#
__all__ = [
    'pxe_handler', 
    'ipv4_handler',

    'AssignFunc',
    'Assignment',
    'PxeTftpConfig',
    'PxeDynConfig',
    'PxeConfig',
    'Cache',
]

#: typehint for optional cache
OptCache = Optional['Cache']

#: typehint definition for assignment function
AssignFunc = Callable[[str], 'Assignment']

#: set of pxe supported option-codes
PXE_OPTIONS = {
    OptionCode.TFTPServerName,
    OptionCode.TFTPServerAddress,
    OptionCode.TFTPServerIPAddress,
    OptionCode.BootfileName,
    OptionCode.PXELinuxPathPrefix,
}

#** Functions **#

def _getopt(req: Message, opcode: OptionCode) -> Any:
    """retrieve bytes associated w/ opcode if in request else none"""
    op = req.options.get(opcode)
    return op.value if op else None

def _enum(value: Union[int, str, IntEnum], enum: Type[IntEnum]):
    """convert value to int-enum"""
    if isinstance(value, int):
        return enum(value)
    elif isinstance(value, str):
        return enum[value]
    elif isinstance(value, enum):
        return value
    else:
        raise ValueError(f'Invalid {enum}: {value!r}')

def pxe_handler(rootcfg: 'PxeConfig') -> HandlerFunc:
    """
    generate session handler for dhcp pxe assignment

    :param rootcfg: root pxe configuration settings
    :return:        session handler function
    """
    def assign_pxe(ctx: Context):
        """
        DHCP PXE Assignment Function

        :param ctx: request/response context
        """
        sess, req, res = ctx
        # skip any assignment if no options are requested
        options = set(req.requested_options())
        if not any(op for op in PXE_OPTIONS if op in options):
            return
        # determine config based on default or or arch/vendor specific
        hwaddr = ctx.request.client_hw.hex()
        config = rootcfg
        subcfg = None
        arches = _getopt(req, OptionCode.ClientSystemArchitectureType)
        vendor = _getopt(req, OptionCode.ClassIdentifier)
        if not subcfg and arches and config.dynamic:
            sess.logger.debug(f'{hwaddr} arches={arches!r}')
            for arch in arches:
                subcfg = config.dynamic.arches.get(arch)
                if subcfg:
                    break
        if not subcfg and vendor and config.dynamic:
            vendor = vendor.decode()
            sess.logger.debug(f'{hwaddr} vendor={vendor!r}')
            for vid, match in config.dynamic.vendors.items():
                if match in vendor:
                    subcfg = config.dynamic.configs.get(vid)
                    sess.logger.debug(f'{hwaddr} vendor match {vid} {match}')
                    if subcfg:
                        break
        # build config from subconfig
        if subcfg:
            config = copy(config)
            config.ipaddr   = subcfg.ipaddr or config.ipaddr
            config.hostname = subcfg.hostname or config.hostname
            config.filename = subcfg.filename or config.filename
        # build options based on config and logging message
        message = [f'{sess.addr_str} | {req.client_hw.hex()}']
        message.append(f'-> pxe={config.ipaddr}')
        res.server_addr = config.ipaddr
        res.options.append(OptTFTPServerIP(config.ipaddr))
        if config.primary:
            res.boot_file   = config.filename or res.boot_file
            res.server_name = config.hostname or res.server_name
        if config.prefix:
            res.options.append(OptPXEPathPrefix(config.prefix))
            message.append(f'root={config.prefix.decode()!r}')
        if config.hostname:
            res.options.append(OptTFTPServerName(config.hostname))
            message.append(f'host={config.hostname.decode()!r}')
        if config.filename:
            res.options.append(OptBootFile(config.filename))
            message.append(f'file={config.filename.decode()!r}')
        sess.logger.info(' '.join(message))
    return assign_pxe

def ipv4_handler(func: AssignFunc, cache: OptCache = None) -> HandlerFunc:
    """
    generate session handler for dhcp ipv4 assignment

    :param func:  assignment function
    :param cache: optional cache to use when generating assignments
    :return:      session handler function
    """
    @wraps(func)
    def assign_ipv4(ctx: Context):
        """
        DHCP IP-LEASE Assignment Function

        :param ctx: request/response context
        """
        sess, req, res = ctx
        hwaddr = req.client_hw.hex()
        assign = cache.get(hwaddr) if cache else None
        assign = assign or func(hwaddr)
        # log assignment
        dns = ','.join(str(dns) for dns in assign.dns)
        sess.logger.info(
            f'{sess.addr_str} | {hwaddr} -> ip={assign.ipaddr} ' + \
            f'gw={assign.gateway} dns={dns} lease={assign.lease}')
        # assign data to response
        res.your_addr = assign.ipaddr.ip
        res.options.extend([
            OptDNS(assign.dns),
            OptRouter(assign.gateway),
            OptSubnetMask(assign.ipaddr.netmask),
            OptIPLeaseTime(int(assign.lease.total_seconds())),
        ])
    return assign_ipv4

#** Classes **#

class Assignment(NamedTuple):
    """IP Assignment Function"""
    dns:     List[IPv4Address]
    ipaddr:  IPv4Interface
    gateway: IPv4Address
    lease:   timedelta

@dataclass
class PxeTftpConfig:
    """Dynamic TFTP PXE Configuration"""
    filename: bytes
    hostname: Optional[bytes]       = None
    ipaddr:   Optional[IPv4Address] = None

ArchT = Union[int, str, Arch]

@dataclass
class PxeDynConfig:
    """Dynamic PXE Configuration Settings and Translations"""
    vendors: Dict[str, str]             = field(default_factory=dict)
    arches:  Dict[ArchT, PxeTftpConfig] = field(default_factory=dict)
    configs: Dict[str, PxeTftpConfig]   = field(default_factory=dict)

    def __post_init__(self):
        """validate and ensure arches are arch-enums"""
        self.arches  = {_enum(k, Arch):v for k, v in self.arches.items()}

@dataclass
class PxeConfig:
    """DHCP PXE Confguration Settings"""
    ipaddr:   IPv4Address
    primary:  bool            = False
    prefix:   Optional[bytes] = None
    hostname: Optional[bytes] = None
    filename: Optional[bytes] = None
    dynamic:  PxeDynConfig    = field(default_factory=PxeDynConfig)

class CacheRecord(NamedTuple):
    """Cache Record Instance"""
    assign:     Any
    expiration: Optional[datetime]

class Cache:
    """ThreadSafe Expiring Cache Implementation"""
    __slots__ = ('expiration', 'maxsize', 'mutex', 'cache')

    def __init__(self, 
        expiration: Optional[timedelta] = None, 
        maxsize:    Optional[int]       = None,
    ):
        self.expiration = expiration
        self.maxsize    = maxsize
        self.mutex      = Lock()
        self.cache: Dict[str, CacheRecord] = {}

    def get(self, key: str) -> Any:
        """retrieve non-expired key from cache"""
        if key not in self.cache:
            return
        with self.mutex:
            record = self.cache[key]
            if record.expiration and record.expiration <= datetime.now():
                del self.cache[key]
                return
            return record.assign

    def put(self, key: str, value: Any):
        """save new assignment to cache"""
        with self.mutex:
            # clear cache until under max-size
            while self.maxsize and len(self.cache) >= self.maxsize:
                self.cache.popitem()
            # assign expiration
            expiration = None
            if self.expiration:
                expiration = datetime.now() + self.expiration
            self.cache[key] = CacheRecord(value, expiration)

    def delete(self, key: str):
        """delete potential key from cache"""
        if key in self.cache:
            with self.mutex:
                self.cache.pop(key)
