from tortoise.queryset import QuerySet
from typing import Dict, Any, Tuple
from sanic.log import logger
import asyncio

refresh_time = 60 * 30 # 30 minutes

queryset_cache: Dict[str, Tuple[Any, QuerySet]] = {}
original_await = QuerySet.__await__

def __await__(self: QuerySet) -> Any:
    self._make_query()

    if self.query in queryset_cache:
        result = queryset_cache[self.query][0]
        async def _wrapper() -> Any:
            return result
        
        yield from _wrapper().__await__()

        return result
    else:
        result = original_await(self)
        
        result_value = (yield from result)

        if "LIMIT 1" not in self.query:
            queryset_cache[self.query] = (result_value, self)

            # schedule a refresh after 'refresh_time' seconds

            async def _refresh() -> None:
                await asyncio.sleep(refresh_time)
                del queryset_cache[self.query]

            asyncio.ensure_future(_refresh())

        async def _wrapper() -> Any:
            return result_value
        
        yield from _wrapper().__await__()

        return result_value


def use_cache() -> None:
    QuerySet.__await__ = __await__