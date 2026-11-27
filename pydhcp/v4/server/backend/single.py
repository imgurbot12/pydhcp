"""
Single-Flight DHCP Backend Optimization Layer
"""
from copy import copy
from typing import Callable, ClassVar, Coroutine, Optional

from pyserve import Address
from pyserve.utils import FlightSrc, SingleFlight as FlightManager

from . import Answer, Backend
from ... import Message

#** Variables **#
__all__ = ['SingleFlight']

Func = Callable[[Address, Message], Coroutine[None, None, Optional[Answer]]]

#** Classes **#

class SingleFlight(Backend):
    """
    Single-Flight DHCP Backend Optimization Layer
    """
    source: ClassVar[str] = 'SingleFlight'

    __slots__ = ('backend', 'manager', 'wrap_label')

    def __init__(self,
        backend:    Backend,
        manager:    Optional[FlightManager] = None,
        wrap_label: Optional[bool]          = True,
    ):
        self.backend    = backend
        self.manager    = manager or FlightManager()
        self.wrap_label = wrap_label

    async def _wrap(self,
        func: Func, address: Address, request: Message) -> Optional[Answer]:
        """
        Wrap backend function with single-flight manager
        Modify the source label if configured to do so
        """
        key         = f'{func.__name__}:{request.client_hw}'
        task        = func(address, request)
        answer, src = await self.manager.do_labeled(key, task)
        if self.wrap_label and src == FlightSrc.FOLLOWER and answer is not None:
            answer = copy(answer)
            answer.source_label = f'{self.source}({answer.source})'
        return answer

    async def discover(self, address: Address, request: Message) -> Optional[Answer]:
        return await self._wrap(self.backend.discover, address, request)

    async def request(self, address: Address, request: Message) -> Optional[Answer]:
        return await self._wrap(self.backend.request, address, request)

    async def decline(self, address: Address, request: Message) -> Optional[Answer]:
        return await self._wrap(self.backend.decline, address, request)

    async def release(self, address: Address, request: Message) -> Optional[Answer]:
        return await self._wrap(self.backend.release, address, request)
