import asyncio
import time
from typing import Dict, Any, Tuple, Union, Callable, List, Optional, Awaitable

from sanic.log import logger
from sanic.request import Request
from tortoise.queryset import QuerySet
from db.types import Permission

refresh_time_queryset = 60 * 30  # 30 minutes
refresh_time_function = 0  # 0 seconds

queryset_cache: Dict[str, Tuple[Any, QuerySet]] = {}
function_cache: Dict[str, Any] = {}
function_cache_enabled = False
original_await = QuerySet.__await__

# list of funtions to save in cache when the server starts
precached_functions: Dict[Callable, Tuple[List, Dict]] = {}
precached_templates: Dict[Callable, Tuple[List, Dict]] = {}

# list of rules for determining what arguments to use for precaching (if dynamically needed)
precached_rules: Dict[Callable, Awaitable] = {}
precached_template_rules: Dict[Callable, Awaitable] = {}


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


def flush_cache(flush_queryset: bool = True, flush_function: bool = True) -> None:
    if flush_queryset:
        queryset_cache.clear()
    if flush_function:
        function_cache.clear()
    logger.info("Cache flushed")


# cache decorator (modified from aiocache.cached)
# ttl: time to live in seconds
# refresh_in_background: whether to refresh the cache in the background after ttl seconds
def cache(ttl: Union[float, int] = refresh_time_function, refresh_in_background: bool = True):
    def decorator(f):
        async def wrapper(*args, **kwargs):
            if not function_cache_enabled:
                return await f(*args, **kwargs)

            request = None
            request_args = None
            if len(args) > 0 and isinstance(args[0], Request):
                request: Request = args[0]
                request_args = request.args

            request = None
            request_args = None
            request_json = None
            if len(args) > 0 and isinstance(args[0], Request):
                request: Request = args[0]
                request_args = request.args
                request_json = request.json

            key = f"{f.__name__}_{args}_{kwargs}"
            if request_args:
                key += f"_{request_args}"
            if request_json:
                key += f"_{request_json}"
            result = None

            if key in function_cache:
                logger.debug(f"Cache hit for {key}")
                result = function_cache[key][0]
                ttl_left = function_cache[key][1] - time.time()
                logger.debug(f"TTL left for {key}: {ttl_left}")

                if refresh_in_background and ttl_left < 0:
                    async def _refresh() -> None:
                        logger.debug(f"Refreshing cache for {key}")

                        result = await f(*args, **kwargs)
                        function_cache[key] = (result, time.time() + ttl)
                        logger.debug(f"Cache refreshed for {key}")

                    asyncio.ensure_future(_refresh())
            else:
                logger.debug(f"Cache miss for {key}")

                result = await f(*args, **kwargs)
                function_cache[key] = (result, time.time() + ttl)
            return result
        
        wrapper.__name__ = f.__name__

        return wrapper

    return decorator

# refresh cache for template

async def refresh_template(f, *args, ttl: Union[float, int] = refresh_time_function, **kwargs) -> Any:
    if not function_cache_enabled:
        return
    
    key = _create_cache_key(f, args, kwargs)

    logger.debug(f"Refreshing cache for {key}")

    result = await f(*args, **kwargs)
    function_cache[key] = (result, time.time() + ttl)
    logger.debug(f"Cache refreshed for {key}")

    return result


def _create_cache_key(f, args, kwargs) -> str:
    key = f"{f.__name__}_{args}_{kwargs}"
    if len(args) > 0 and isinstance(args[0], Request):
        request: Request = args[0]
        request_args = request.args
        request_json = request.json
        if request_args:
            key += f"_{request_args}"
        if request_json:
            key += f"_{request_json}"
        logger.debug(
            f"Creating cache key for {f.__name__} with args: {args} and kwargs: {kwargs}, request_args: {request_args}, request_json: {request_json} => {key}"
        )
    else:
        logger.debug(f"Creating cache key for {f.__name__} with args: {args} and kwargs: {kwargs} => {key}")

    return key

def cache_template(ttl: Union[float, int] = refresh_time_function, refresh_in_background: bool = True):
    # cache the results of the template
    def decorator(f):
        async def wrapper(*args, **kwargs) -> str:
            if not function_cache_enabled:
                args = await f(*args, **kwargs)
                from utils import render_template
                return await render_template(args[0], args[1], *args[2], **args[3])
            
            key = _create_cache_key(f, args, kwargs)
            
            result = None

            if key in function_cache:
                logger.debug(f"Cache hit for {key}")
                result = function_cache[key][0]
                ttl_left = function_cache[key][1] - time.time()
                logger.debug(f"TTL left for {key}: {ttl_left}")

                if refresh_in_background and ttl_left < 0:
                    asyncio.ensure_future(refresh_template(f, *args, **kwargs, ttl=ttl))
            else:
                logger.debug(f"Cache miss for {key}")

                result = await refresh_template(f, *args, **kwargs, ttl=ttl)
            from utils import render_template
            return await render_template(args[0], result[1], *result[2], **result[3])

        wrapper.__name__ = f.__name__

        return wrapper

    return decorator

def precache(*args, rule: Optional[Awaitable] = None, **kwargs) -> Callable:
    """
    Decorator to precache the result of a function.

    @precache([arg1, arg2], [arg1, arg2])

    If `rule` is provided, it will be used to determine what argument lists to use for precaching
    using a function to dynamically generate the argument lists.

    @precache(rule=function)
    """
    

    def decorator(f):
        args_ = args

        if rule is not None:
            precached_rules[f] = rule
        elif len(args) == 0:
            args_ = [[]] # ensure args is a list of lists
            
        for arglist in args_:
            if precached_functions.get(f):
                precached_functions[f].append((arglist, kwargs))
            else:
                precached_functions[f] = [(arglist, kwargs)]

        return f
    
    return decorator

def precache_template(*args, rule: Optional[Awaitable] = None, **kwargs) -> Callable:
    """
    Decorator to precache the result of a template.

    @precache_template([arg1, arg2], [arg1, arg2])

    If `rule` is provided, it will be used to determine what argument lists to use for precaching
    using a function to dynamically generate the argument lists.

    @precache_template(rule=function)
    """
    def decorator(f):
        args_ = args

        if rule is not None:
            precached_template_rules[f] = rule
        elif len(args) == 0:
            args_ = [[]] # ensure args is a list of lists
        
        for arglist in args_:
            if precached_templates.get(f):
                precached_templates[f].append((arglist, kwargs))
            else:
                precached_templates[f] = [(arglist, kwargs)]

        return f
    
    return decorator

async def precache_all_functions() -> None:
    """
    Actually precache the functions/templates that were decorated with @precache or @precache_template.

    We can't do this when the decorator is called because the server isn't started yet,
    and the db isn't connected, so we can't run the function.

    Run this function (in the background) after the server starts to precache all functions.
    """

    # add the dynamic precache rules

    for f, rule in precached_rules.items():
        if asyncio.iscoroutinefunction(rule):
            arglists = await rule()
        else:
            raise TypeError(f"Precache rule for {f.__name__} must be a coroutine function")

        for args in arglists:
            if precached_functions.get(f):
                precached_functions[f].append((args, {}))
            else:
                precached_functions[f] = [(args, {})]
    
    for f, rule in precached_template_rules.items():
        if asyncio.iscoroutinefunction(rule):
            arglists = await rule()
        else:
            raise TypeError(f"Precache rule for {f.__name__} must be a coroutine function")

        for args in arglists:
            if precached_templates.get(f):
                precached_templates[f].append((args, {}))
            else:
                precached_templates[f] = [(args, {})]


    async def cache(f, *args, **kwargs) -> None:
        # not checking if cache is enabled because the server can't enable it until it starts

        key = _create_cache_key(f, args, kwargs)
        logger.debug(f"Pre-caching {key} with args: {args} and kwargs: {kwargs}")

        result = await f(*args, **kwargs)
        function_cache[key] = (result, time.time() + refresh_time_function)

        logger.debug(f"Pre-cache complete for {key}")

    for f, arglists in precached_functions.items():
        for args, kwargs in arglists:
            asyncio.ensure_future(cache(f, *args, **kwargs))

    for f, arglists in precached_templates.items():
        for args, kwargs in arglists:
            from shared import app
            route = app.router.find_route_by_view_name(f.__name__)

            method, = route.methods # get first method from the route
            
            request = Request(bytes(route.uri, encoding="utf-8"), {}, "", method, None, app)

            args = list(args)
            args.insert(0, request)
            request.ctx.session = {
                "permissions": Permission.USER
            }
            
            asyncio.ensure_future(cache(f, *args, **kwargs))