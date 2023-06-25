"""
DHCP Unique Identifier (DUID) Implementations (rfc8415 section-11)
"""
from datetime import datetime, timedelta, timezone
from typing import ClassVar
from typing_extensions import Annotated

from pystructs import *

from .enum import DuidType
from ..enum import HwType

#** Variables **#
__all__ = [
    'read_duid',
    'write_duid',

    'DUID',
    'LinkLayerPlusTime',
    'EnterpriseNumber',
    'LinkLayer',
    'UniqueIdentifier',
]

#: codec handler for HwType enum
HwInt = Annotated[HwType, Wrap[U16, HwType]]

#: January 1, 2000 UTC
EPOCH = datetime(year=2000, month=1, day=1, tzinfo=timezone.utc)

#** Functions **#

def read_duid(raw: bytes) -> 'DUID':
    """
    read duid struct from raw bytes
    """
    ctx    = Context()
    duid   = DuidType(decode(ctx, raw, U8))
    dclass = DUIDS.get(duid, None)
    if dclass is None:
        raise ValueError(f'Unsupported DUID: {duid!r}')
    return dclass.decode(ctx, raw)

def write_duid(duid: 'DUID'):
    """
    serialize duid struct into raw bytes
    """
    ctx = Context()
    return encode(ctx, U16, duid.duid) + duid.encode(ctx)

#** Classes **#

class Datetime(datetime):
 
    def __new__(cls, time: int, *args):
        # support standard datetime actions when extra vars are passed
        if args:
            return super().__new__(cls, time, *args)
        # process seconds declaration when parsing data
        dt = (EPOCH + timedelta(seconds=time)).astimezone(tz=None)
        return super().__new__(cls, 
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    def __int__(self) -> int:
        return int(self.timestamp())

class DUID(Struct):
    duid: ClassVar[DuidType]

class LinkLayerPlusTime(DUID):
    duid = DuidType.LinkLayerPlusTime
    hw_type: HwInt
    time:    Annotated[int, Wrap[U32, Datetime]]
    address: GreedyBytes

class EnterpriseNumber(DUID):
    duid = DuidType.EnterpriseNumber
    en:         U16
    en_contd:   U16
    identifier: GreedyBytes

class LinkLayer(DUID):
    duid = DuidType.LinkLayer
    hw_type: HwInt
    address: GreedyBytes

class UniqueIdentifier(DUID):
    duid = DuidType.UniqueIdentifier
    uuid: StaticBytes[128]

#** Classes **#

#: map of duid enum to valid subclasses
DUIDS = {
    duid.duid:duid
    for duid in globals().values()
    if isinstance(duid, type) and issubclass(duid, DUID) and duid is not DUID
}
