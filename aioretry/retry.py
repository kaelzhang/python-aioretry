import sys

from typing import (
    Tuple,
    Any,
    Union,
    Callable,
    Awaitable,
    Optional,
    TypeVar,
)

# Import ParamSpec if supported
if sys.version_info >= (3, 10):
    from typing import ParamSpec

    PS = ParamSpec('PS')
else:
    from typing_extensions import ParamSpec # pragma: no cover

    PS = ParamSpec('PS') # pragma: no cover


import warnings
import inspect
import asyncio
import time


class RetryInfo:
    __slots__ = (
        'fails',
        'exception',
        'since'
    )

    fails: int
    exception: Exception
    since: float

    def __init__(
        self,
        fails: int,
        exception: Exception,
        since: float
    ) -> None:
        self.fails = fails
        self.exception = exception
        self.since = since

    def update(
        self,
        exception: Exception
    ) -> 'RetryInfo':
        """Create a new RetryInfo and update fails and exception

        Why?
            The object might be collected by user, so we need to create a new object every time it fails.
        """

        return RetryInfo(
            self.fails + 1,
            exception,
            self.since
        )


RetryPolicyStrategy = Tuple[bool, Union[int, float]]

RetryPolicyRT = Union[RetryPolicyStrategy, Awaitable[RetryPolicyStrategy]]
RetryPolicy = Callable[[RetryInfo], RetryPolicyRT]

BeforeRetryRT = Optional[Awaitable[None]]
BeforeRetry = Callable[[RetryInfo], BeforeRetryRT]

ParamRetryPolicy = Union[RetryPolicy, str]
ParamBeforeRetry = Union[BeforeRetry, str]

Exceptions = Tuple[Exception, ...]
ExceptionsOrException = Union[Exceptions, Exception]

T = TypeVar('T', RetryPolicy, BeforeRetry)

# Return type
RT = TypeVar('RT')
TargetFunction = Callable[PS, Awaitable[RT]]


async def await_coro(coro: BeforeRetryRT) -> None:
    if inspect.isawaitable(coro):
        await coro


def warn(method_name: str, exception: Exception):
    warnings.warn(
        f"""[aioretry] {method_name} raises an exception:
    {exception}
It is usually a bug that you should fix!""",
        UserWarning,
        stacklevel=2
    )


async def perform(
    fn: TargetFunction[PS, RT],
    retry_policy: RetryPolicy,
    before_retry: Optional[BeforeRetry],
    *args: PS.args,
    **kwargs: PS.kwargs,
) -> RT:
    info = None

    while True:
        try:
            return await fn(*args, **kwargs)
        except Exception as fne:
            if info is None:
                info = RetryInfo(1, fne, time.monotonic())
            else:
                info = info.update(fne)

            try:
                retry_policy_rt = retry_policy(info)

                abandon, delay = (
                    await retry_policy_rt
                    if inspect.isawaitable(retry_policy_rt)
                    else retry_policy_rt
                )
            except Exception as pe:
                warn('retry_policy', pe)
                raise pe

            if abandon:
                raise fne

            if before_retry is not None:
                try:
                    await await_coro(before_retry(info))
                except Exception as be:
                    warn('before_retry', be)
                    raise be

            # `delay` could be 0
            if delay > 0:
                await asyncio.sleep(delay)


def get_method(
    target: Union[T, str],
    host: Any,
    name: str,
) -> T:
    # mypy is sooooo stupid, we should never assign this to a variable,
    # or the type inference will be wrong
    if isinstance(target, str):
        if host is None:
            raise RuntimeError(
                f'[aioretry] decorator should be used for instance method if {name} as a str "{target}", which should be fixed'
            )

        return getattr(host, target)  # type: ignore

    if host is None:
        return target

    cls = type(host)

    if (
        # `target` could be a wrapped classmethod even without
        # attaching to the class of the current instance (host)
        isinstance(target, classmethod)
        # similar to classmethod
        or isinstance(target, staticmethod)

        # Make sure the method is defined in the class
        or target == getattr(cls, target.__name__, None)
    ):
        # Bind the target to the host and its class, which allows that
        # the `target` could be executed in the current class context
        return target.__get__(host, cls) # type: ignore

    return target


def retry(
    retry_policy: ParamRetryPolicy,
    before_retry: Optional[ParamBeforeRetry] = None,
) -> Callable[[TargetFunction[PS, RT]], TargetFunction[PS, RT]]:
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

    def wrapper(fn: TargetFunction[PS, RT]) -> TargetFunction[PS, RT]:
        async def wrapped(*args: PS.args, **kwargs: PS.kwargs) -> RT:
            host = args[0] if len(args) > 0 else None

            return await perform(
                fn,
                get_method(retry_policy, host, 'retry_policy'),
                (
                    get_method(before_retry, host, 'before_retry')
                    if before_retry is not None
                    else None
                ),
                *args,
                **kwargs,
            )

        return wrapped

    return wrapper
