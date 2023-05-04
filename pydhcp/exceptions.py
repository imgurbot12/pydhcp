"""
Universal DHCP Exceptions based on IANA StatusCodes
"""
from typing import Dict, Type, Any, Optional

from .enum import StatusCode

#** Variables **#
__all__ = [
    'make_error',

    'DhcpError',
    'NoAddrsAvailable',
    'NotAllowed',
    'NotSupported',
    'MalformedQuery',
    'Terminated',
    'UnknownQueryType',
]

_EXCEPTIONS: Dict[StatusCode, Type[Exception]] = {}

#** Functions **#

def make_error(code: StatusCode, message: Any = None):
    """
    retrieve best exception object to match the given rcode
    """
    # cache map of exceptions in module
    global _EXCEPTIONS
    if not _EXCEPTIONS:
        for value in globals().values():
            if isinstance(value, type) and issubclass(value, DhcpError):
                _EXCEPTIONS[value.code] = value
    # retrieve best-matching exception class based on rcode
    eclass = _EXCEPTIONS.get(code, DhcpError)
    raise eclass(message, code)

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

class NoAddrsAvailable(DhcpError):
    code = StatusCode.NoAddrsAvail

class NotAllowed(DhcpError):
    code = StatusCode.NotAllowed

class NotSupported(DhcpError):
    code = StatusCode.NotSupported

class MalformedQuery(DhcpError):
    code = StatusCode.MalformedQuery

class UnknownQueryType(DhcpError):
    code = StatusCode.UnknownQueryType

class Terminated(DhcpError):
    code = StatusCode.QueryTerminated
