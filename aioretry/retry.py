from typing import (
    Tuple,
    Union,
    Callable,
    Coroutine,
    Optional,
    TypeVar,
)

import warnings
import inspect
import asyncio
from datetime import datetime


class RetryInfo:
    __slots__ = ("fails", "exception", "since")

    fails: int
    exception: Exception
    since: datetime

    def __init__(self, fails: int, exception: Exception, since: datetime) -> None:
        self.fails = fails
        self.exception = exception
        self.since = since

    def update(self, exception: Exception) -> "RetryInfo":
        """Create a new RetryInfo and update fails and exception

        Why?
            The object might be collected by user, so we need to create a new object every time it fails.
        """

        return RetryInfo(self.fails + 1, exception, self.since)


RetryPolicyStrategy = Tuple[bool, Union[int, float]]

RetryPolicy = Callable[[RetryInfo], RetryPolicyStrategy]
BeforeRetry = Callable[[RetryInfo], Optional[Coroutine[None, None, None]]]

ParamRetryPolicy = Union[RetryPolicy, str]
ParamBeforeRetry = Union[BeforeRetry, str]

# we imply that TargetFunction does not have yield and send types.
TargetFunctionR = TypeVar("TargetFunctionR")
TargetFunction = Callable[..., Coroutine[None, None, TargetFunctionR]]
Exceptions = Tuple[Exception, ...]
ExceptionsOrException = Union[Exceptions, Exception]

T = TypeVar("T", RetryPolicy, BeforeRetry)


async def await_coro(coro):
    if inspect.isawaitable(coro):
        return await coro

    return coro


def warn(method_name: str, exception: Exception):
    warnings.warn(
        f"""[aioretry] {method_name} raises an exception:
    {exception}
It is usually a bug that you should fix!""",
        UserWarning,
        stacklevel=2,
    )


async def perform(
    fn: TargetFunction,
    retry_policy: RetryPolicy,
    before_retry: Optional[BeforeRetry],
    *args,
    **kwargs,
):
    info = None

    while True:
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            if info is None:
                info = RetryInfo(1, e, datetime.now())
            else:
                info = info.update(e)

            try:
                abandon, delay = retry_policy(info)
            except Exception as e:
                warn("retry_policy", e)
                raise

            if abandon:
                raise

            if before_retry is not None:
                try:
                    await await_coro(before_retry(info))
                except Exception as e:
                    warn("before_retry", e)
                    raise

            # `delay` could be 0
            if delay > 0:
                await asyncio.sleep(delay)


def get_method(
    target: Union[T, str],
    args: Tuple,
    name: str,
) -> T:
    if not isinstance(target, str):
        return target

    if len(args) == 0:
        raise RuntimeError(
            f'[aioretry] decorator should be used for instance method if {name} as a str "{target}", which should be fixed'
        )

    self = args[0]

    return getattr(self, target)  # type: ignore


def retry(
    retry_policy: ParamRetryPolicy,
    before_retry: Optional[ParamBeforeRetry] = None,
) -> Callable[[TargetFunction], TargetFunction]:
    """Creates a decorator function

    Args:
        retry_policy (RetryPolicy, str): the retry policy
        before_retry (BeforeRetry, str, None): the function to be called after each failure of fn and before the corresponding retry.

    Returns:
        A wrapped function which accepts the same arguments as fn and returns an Awaitable

    Usage::
        @retry(retry_policy)
        async def coro_func():
            ...
    """

    def wrapper(fn: TargetFunction) -> TargetFunction:
        async def wrapped(*args, **kwargs):
            return await perform(
                fn,
                get_method(retry_policy, args, "retry_policy"),
                get_method(before_retry, args, "before_retry")
                if before_retry is not None
                else None,
                *args,
                **kwargs,
            )

        return wrapped

    return wrapper
