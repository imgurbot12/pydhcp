"""
SimpleSession Handler Implentations
"""
from copy import copy
from functools import wraps
from datetime import datetime, timedelta
from ipaddress import IPv4Address, IPv4Interface
from typing import Callable, NamedTuple, List, Optional, Dict, Any
from threading import Lock

from pyderive import dataclass

from .server import HandlerFunc
from ..message import Message, OptionCode
from ..options import *
from ...base import Seconds

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

def pxe_handler(rootcfg: 'PxeConfig') -> HandlerFunc:
    """
    generate session handler for dhcp pxe assignment

    :param rootcfg: root pxe configuration settings
    :return:        session handler function
    """
    def assign_pxe(req: Message, res: Message):
        """
        DHCP PXE Assignment Function

        :param req: dhcp request
        :param res: dhcp response
        """
        # skip any assignment if no options are requested
        options = set(req.requested_options())
        if any(op for op in PXE_OPTIONS if op in options):
            return
        # determine config based on default or vendor specific
        config = rootcfg
        vendor = req.options.get(OptionCode.ClassIdentifier)
        vendor = vendor.value.decode() if vendor else None
        if vendor and config.dynamic:
            for vid, match in config.dynamic.vendors.items():
                if match not in vendor:
                    continue
                config    = copy(config)
                subconfig = config.dynamic.configs[vid]
                config.ipaddr   = subconfig.ipaddr or config.ipaddr
                config.hostname = subconfig.hostname or config.hostname
                config.filename = subconfig.filename or config.filename
                break
        # build options based on config
        res.server_addr = config.ipaddr
        res.options.append(OptTFTPServerIP(config.ipaddr))
        if config.primary:
            res.boot_file   = config.filename or res.boot_file
            res.server_name = config.hostname or res.server_name
        if config.prefix:
            res.options.append(OptPXEPathPrefix(config.prefix))
        if config.hostname:
            res.options.append(OptTFTPServerName(config.hostname))
        if config.filename:
            res.options.append(OptBootFile(config.filename))
    return assign_pxe

def ipv4_handler(func: AssignFunc, cache: OptCache = None) -> HandlerFunc:
    """
    generate session handler for dhcp ipv4 assignment

    :param func:  assignment function
    :param cache: optional cache to use when generating assignments
    :return:      session handler function
    """
    @wraps(func)
    def assign_ipv4(req: Message, res: Message):
        """
        DHCP IP-LEASE Assignment Function

        :param req: dhcp request
        :param res: dhcp response
        """
        hwaddr = req.client_hw.hex()
        assign = cache.get(hwaddr) if cache else None
        assign = assign or func(hwaddr)
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

@dataclass(slots=True)
class PxeTftpConfig:
    """Dynamic TFTP PXE Configuration"""
    filename: bytes
    hostname: Optional[bytes]       = None
    ipaddr:   Optional[IPv4Address] = None

@dataclass(slots=True)
class PxeDynConfig:
    """Dynamic PXE Configuration Settings and Translations"""
    vendors: Dict[str, str]
    configs: Dict[str, PxeTftpConfig]

@dataclass(slots=True)
class PxeConfig:
    """DHCP PXE Confguration Settings"""
    ipaddr:   IPv4Address
    primary:  bool                   = False
    prefix:   Optional[bytes]        = None
    hostname: Optional[bytes]        = None
    filename: Optional[bytes]        = None
    dynamic:  Optional[PxeDynConfig] = None

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
