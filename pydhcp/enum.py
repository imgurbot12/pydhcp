"""
Global Enum Types for DHCP v4/v6
"""
from enum import IntEnum

#** Variables **#
__all__ = ['Arch', 'HwType', 'StatusCode']

#** Classes **#

class Arch(IntEnum):
    """
    Hardware Architecture Type (RFC 4578, Section 2.1.)
    """
    INTEL_X86PC       = 0
    NEC_PC98          = 1
    EFI_ITANIUM       = 2
    DEC_ALPHA         = 3
    ARC_X86           = 4
    INTEL_LEAN_CLIENT = 5
    EFI_IA32          = 6
    EFI_BC            = 7
    EFI_XSCALE        = 8
    EFI_X86_64        = 9

class HwType(IntEnum):
    """
    Number Hardware Type (hrd) (RFC 1700)
    """
    Ethernet             = 1
    ExperimentalEthernet = 2
    AmateurRadioAX25     = 3
    ProteonTokenRing     = 4
    Chaos                = 5
    IEEE802              = 6
    ARCNET               = 7
    Hyperchannel         = 8
    Lanstar              = 9
    Autonet              = 10
    LocalTalk            = 11
    LocalNet             = 12
    UltraLink            = 13
    SMDS                 = 14
    FrameRelay           = 15
    ATM                  = 16
    HDLC                 = 17
    FibreChannel         = 18
    ATM2                 = 19
    SerialLine           = 20
    ATM3                 = 21
    MILSTD188220         = 22
    Metricom             = 23
    IEEE1394             = 24
    MAPOS                = 25
    Twinaxial            = 26
    EUI64                = 27
    HIPARP               = 28
    ISO7816              = 29
    ARPSec               = 30
    IPsec                = 31
    Infiniband           = 32
    CAI                  = 33
    WiegandInterface     = 34
    PureIP               = 35

class StatusCode(IntEnum):
    """
    IANA Status Codes for DHCPv6
    https://www.iana.org/assignments/dhcpv6-parameters/dhcpv6-parameters.xhtml#dhcpv6-parameters-5
    """
    # RFC 3315 par. 24..4
    Success       = 0
    UnspecFail    = 1
    NoAddrsAvail  = 2
    NoBinding     = 3
    NotOnLink     = 4
    UseMulticast  = 5
    NoPrefixAvail = 6
    # RFC 5007
    UnknownQueryType = 7
    MalformedQuery   = 8
    NotConfigured    = 9
    NotAllowed       = 10
    # RFC 5460
    QueryTerminated = 11
    # RFC 7653
    DataMissing          = 12
    CatchUpComplete      = 13
    NotSupported         = 14
    TLSConnectionRefused = 15
    # RFC 8156
    AddressInUse               = 16
    ConfigurationConflict      = 17
    MissingBindingInformation  = 18
    OutdatedBindingInformation = 19
    ServerShuttingDown         = 20
    DNSUpdateNotSupported      = 21
    ExcessiveTimeSkew          = 22
