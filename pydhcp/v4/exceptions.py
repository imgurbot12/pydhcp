"""
DHCPv4 StatusCode Exceptions
"""
from typing import Any, Optional

from ..enum import StatusCode

#** Variables **#
__all__ = [
    'DhcpError',

    'UnknownQueryType',
    'MalformedQuery',
    'NoAddrsAvailable',
    'NotAllowed',
    'Terminated',
    'NotSupported',
    'AddressInUse',
]

#** Classes **#

class DhcpError(Exception):
    code: StatusCode = StatusCode.UnspecFail

    def __init__(self, msg: Any = None, code: Optional[StatusCode] = None):
        self.message = msg
        self.code    = code or self.code

    def __str__(self) -> str:
        if self.message and self.__class__.code == self.code:
            return str(self.message)
        return super().__str__()

class UnknownQueryType(DhcpError):
    code = StatusCode.UnknownQueryType

class MalformedQuery(DhcpError):
    code = StatusCode.MalformedQuery

class NoAddrsAvailable(DhcpError):
    code = StatusCode.NoAddrsAvail

class NotAllowed(DhcpError):
    code = StatusCode.NotAllowed

class Terminated(DhcpError):
    code = StatusCode.QueryTerminated

class NotSupported(DhcpError):
    code = StatusCode.NotSupported

class AddressInUse(DhcpError):
    code = StatusCode.AddressInUse
