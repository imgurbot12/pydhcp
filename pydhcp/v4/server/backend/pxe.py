"""
DHCP PXE TFTP Assignment Backend
"""
from copy import copy
from ipaddress import IPv4Address
from logging import Logger, getLogger
from typing import Any, ClassVar, Dict, Optional
from typing_extensions import Annotated

from pyderive import dataclass, field
from pyderive.extensions.validate import BaseModel, Validator

from . import Address, Answer, Backend
from ... import *
from .... import Arch

#** Variables **#
__all__ = ['PxeTftpConfig', 'PxeDynConfig', 'PxeConfig', 'PXEBackend']

#: set of pxe supported option-codes
PXE_OPTIONS = {
    OptionCode.TFTPServerName,
    OptionCode.TFTPServerAddress,
    OptionCode.TFTPServerIPAddress,
    OptionCode.BootfileName,
    OptionCode.PXELinuxPathPrefix,
}

#** Functions **#

def arch_validator(arch: Any) -> Arch:
    """
    pyderive Arch validator function
    """
    if isinstance(arch, int):
        return Arch(arch)
    if isinstance(arch, str):
        return Arch[arch]
    if isinstance(arch, Arch):
        return arch
    raise ValueError('Invalid Arch: {arch!r}')

#** Classes **#

ArchT = Annotated[Arch, Validator[arch_validator]]

class PxeTftpConfig(BaseModel, typecast=True):
    """
    Dynamic PXE TFTP Configuration Override Settings
    """
    filename: bytes
    """DHCP BootFile (67) PXE Assignment"""
    hostname: Optional[bytes] = None
    """DHCP TFTP Server Name (66) PXE Assignment"""
    ipaddr: Optional[IPv4Address] = None
    """DHCP TFTP Server IP (128) PXE Assignment"""

class PxeDynConfig(BaseModel):
    """
    Dynamic PXE Configuration Settings based on DHCP Request Data
    """
    arches:  Dict[ArchT, PxeTftpConfig] = field(default_factory=dict)
    """Dynamic TFTP Configuration Assignment based on DHCP Client Arch (93)"""
    vendors: Dict[str, str] = field(default_factory=dict)
    """Mapping of DHCP Vendor Class (60) to Configuration Names"""
    configs: Dict[str, PxeTftpConfig] = field(default_factory=dict)
    """Dynamic TFTP Configuration Assignment based on Configuration Names"""

class PxeConfig(BaseModel, typecast=True):
    """
    DHCP PXE Configuration Settings
    """
    ipaddr: IPv4Address
    """DHCP TFTP Server IP (128) PXE Assignment"""
    primary: bool = False
    """Act as Primary DHCP Server and Assign DHCP `file`/`sname` fields"""
    prefix: Optional[bytes] = None
    """DHCP PXE Path Prefix (210) PXE Assignment"""
    hostname: Optional[bytes] = None
    """DHCP TFTP Server Name (66) PXE Assignment"""
    filename: Optional[bytes] = None
    """DHCP BootFile (67) PXE Assignment"""
    dynamic: PxeDynConfig = field(default_factory=PxeDynConfig)
    """Dynamic PXE Configuration Overrides based on DHCP Request Data"""

@dataclass(slots=True)
class PXEBackend(Backend):
    """
    DHCP PXE Assignment Backend based on Static Configuration
    """
    source: ClassVar[str] = 'PXE'

    config:  PxeConfig
    backend: Optional[Backend] = None
    logger:  Logger            = field(default_factory=lambda: getLogger('pydhcp'))

    def get_pxe_config(self, hwaddr: str, request: Message) -> PxeConfig:
        """
        Generate PXE Configuration based on DHCP Request Client Information

        :param hwaddr:  hardware-address (MAC)
        :param request: dhcp request message
        :return:        pxe configuration settings
        """
        # retrieve client information relevant to dynamic assignment
        subcfg = None
        arches = request.options.get(ClientSystemArch)
        vendor = request.options.get(VendorClassIdentifier)
        # attempt to retrieve dynamic sub-config based on arch
        if arches and self.config.dynamic.arches:
            self.logger.debug(f'{hwaddr} arches={arches!r}')
            for arch in arches.arches:
                subcfg = self.config.dynamic.arches.get(arch)
                if subcfg is not None:
                    break
        # attempt to retrieve dynamic sub-config based on vendor
        if not subcfg and vendor and self.config.dynamic:
            vendor = vendor.vendor.decode()
            self.logger.debug(f'{hwaddr} vendor={vendor!r}')
            for vendor_id, match in self.config.dynamic.vendors.items():
                if match in vendor:
                    subcfg = self.config.dynamic.configs.get(vendor_id)
                    self.logger.debug(
                        f'{hwaddr} vendor match {vendor_id} {match}')
                    if subcfg:
                        break
        # override primary config with subconfig (if exists)
        config = self.config
        if subcfg:
            config = copy(config)
            config.ipaddr   = subcfg.ipaddr or config.ipaddr
            config.hostname = subcfg.hostname or config.hostname
            config.filename = subcfg.filename or config.filename
        return config

    def pxe(self,
        address:  Address,
        request:  Message,
        response: Optional[Message] = None,
    ) -> Optional[Message]:
        """
        DHCP Response and PXE Option Assignment

        :param address:  client address
        :param request:  dhcp request message
        :param response: existing dhcp response (if set)
        :return:         dhcp response (if applicable)
        """
        options = request.requested_options()
        if not any(op in PXE_OPTIONS for op in options):
            return response
        # retrieve client information relevant to dynamic assignment
        hwaddr = request.client_hw.hex()
        config = self.get_pxe_config(hwaddr, request)
        # build DHCP options based on configuration
        message  = [f'{address[0]}:{address[1]} | {hwaddr}']
        response = response or request.reply()
        response.server_addr = config.ipaddr
        response.options.append(TFTPServerIP(config.ipaddr.packed))
        message.append(f'-> pxe={str(config.ipaddr)}')
        if config.primary:
            response.boot_file   = config.filename or response.boot_file
            response.server_name = config.hostname or response.server_name
        if config.prefix:
            message.append(f'root={config.prefix.decode()!r}')
            response.options.append(PXEPathPrefix(config.prefix))
        if config.hostname:
            message.append(f'host={config.hostname.decode()!r}')
            response.options.append(TFTPServerName(config.hostname))
        if config.filename:
            message.append(f'file={config.filename.decode()!r}')
            response.options.append(BootfileName(config.filename + b'\x00'))
        self.logger.info(' '.join(message))
        return response

    def discover(self, address: Address, request: Message) -> Optional[Answer]:
        answer = self.backend.discover(address, request) \
            if self.backend else None
        res, src = answer if answer else (None, self.source)
        response = self.pxe(address, request, res)
        return Answer(response, src) if response else None

    def request(self, address: Address, request: Message) -> Optional[Answer]:
        answer = self.backend.request(address, request) \
            if self.backend else None
        res, src = answer if answer else (None, self.source)
        response = self.pxe(address, request, res)
        return Answer(response, src) if response else None

    def release(self, address: Address, request: Message) -> Optional[Answer]:
        if self.backend is not None:
            return self.backend.release(address, request)

    def decline(self, address: Address, request: Message) -> Optional[Answer]:
        if self.backend is not None:
            return self.backend.decline(address, request)
