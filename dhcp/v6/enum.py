"""
DHCPv6 Enums
"""
from enum import IntEnum

#** Variables **#
__all__ = ['MessageType', 'OptionCode', 'DuidType']

#** Classes **#

class MessageType(IntEnum):
    SOLICIT      = 1
    ADVERTIZE    = 2
    REQUEST      = 3
    CONFIRM      = 4
    RENEW        = 5
    REBIND       = 6
    REPLY        = 7
    RELEASE      = 8
    DECLINE      = 9
    RECONFIGURE  = 10
    INFO_REQUEST = 11
    RELAY_FORW   = 12
    RELAY_REPL   = 13

class OptionCode(IntEnum):
    UNKNOWKN               = 0
    ClientIdentifier       = 1
    ServerIdentifier       = 2
    NonTemporaryAddress    = 3
    TemporaryAddress       = 4
    Address                = 5
    OptionRequest          = 6
    Preference             = 7
    ElapsedTime            = 8
    RelayMessage           = 9
    Authentication         = 11
    ServerUnicast          = 12
    StatusCode             = 13
    RapidCommit            = 14
    UserClass              = 15
    VendorClass            = 16
    VendorInfo             = 17
    InterfaceId            = 18
    ReconfMessage          = 19
    ReconfAccept           = 20
    DNSRecurisveNameServer = 23
    DomainSearchList       = 24
    IdAssocPrefixDeleg     = 25
    IAPrefix               = 26
    InfoRefreshTime        = 32
    SOL_MAX_RT             = 82
    INF_MAX_RT             = 83

class DuidType(IntEnum):
    LinkLayerPlusTime = 1
    EnterpriseNumber  = 2
    LinkLayer         = 3
    UniqueIdentifier  = 4
