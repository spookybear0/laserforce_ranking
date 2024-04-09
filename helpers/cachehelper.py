from tortoise.queryset import QuerySet
from typing import Dict, Any, Tuple, Union
from sanic.log import logger
from sanic.request import Request
import asyncio
import time

refresh_time_queryset = 60 * 30 # 30 minutes
refresh_time_function = 0 # 0 seconds

queryset_cache: Dict[str, Tuple[Any, QuerySet]] = {}
function_cache: Dict[str, Any] = {}
function_cache_enabled = False
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

            # schedule a refresh after 'refresh_time_queryset' seconds

            async def _refresh() -> None:
                await asyncio.sleep(refresh_time_queryset)
                del queryset_cache[self.query]

            asyncio.ensure_future(_refresh())

        async def _wrapper() -> Any:
            return result_value
        
        yield from _wrapper().__await__()

        return result_value


def use_cache() -> None:
    global function_cache_enabled
    QuerySet.__await__ = __await__
    function_cache_enabled = True

def flush_cache(flush_queryset: bool=True, flush_function: bool=True) -> None:
    if flush_queryset:
        queryset_cache.clear()
    if flush_function:
        function_cache.clear()
    logger.info("Cache flushed")

# cache decorator (modified from aiocache.cached)
# ttl: time to live in seconds
# refresh_in_background: whether to refresh the cache in the background after ttl seconds
def cache(ttl: Union[float, int]=refresh_time_function, refresh_in_background: bool=True):
    def decorator(f):
        async def wrapper(*args, **kwargs):
            if not function_cache_enabled:
                return await f(*args, **kwargs)
            
            request_args = None
            if len(args) > 0 and isinstance(args[0], Request):
                request: Request = args[0]
                request_args = request.args

            key = f"{f.__name__}_{args}_{kwargs}"
            if request_args:
                key += f"_{request_args}"
            result = None

            if key in function_cache:
                logger.debug(f"Cache hit for {key}")
                result = function_cache[key][0]
                ttl_left = function_cache[key][1] - time.time()
                logger.debug(f"TTL left for {key}: {ttl_left}")

                if refresh_in_background and ttl_left < 0:
                    async def _refresh() -> None:
                        logger.debug(f"Refreshing cache for {key}")
                        del function_cache[key]
                        result = await f(*args, **kwargs)
                        function_cache[key] = (result, time.time() + ttl)
                        logger.debug(f"Cache refreshed for {key}")

                    asyncio.ensure_future(_refresh())
            else:
                logger.debug(f"Cache miss for {key}")
                result = await f(*args, **kwargs)
                function_cache[key] = (result, time.time() + ttl)
            return result

        return wrapper
    return decorator