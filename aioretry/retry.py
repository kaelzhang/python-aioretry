from typing import (
    Tuple,
    Union,
    Callable,
    Awaitable,
    Optional,
    TypeVar
)

import inspect
import asyncio


RetryPolicyStrategy = Tuple[bool, Union[int, float]]

RetryPolicy = Callable[[int], RetryPolicyStrategy]
AfterFailure = Callable[[Exception, int], Optional[Awaitable]]

ParamRetryPolicy = Union[RetryPolicy, str]
ParamAfterFailure = Union[AfterFailure, str]

TargetFunction = Callable[..., Awaitable]

T = TypeVar('T', RetryPolicy, AfterFailure)


async def await_coro(coro):
    if inspect.isawaitable(coro):
        return await coro

    return coro


async def perform(
    fails: int,
    fn: TargetFunction,
    retry_policy: RetryPolicy,
    after_failure: Optional[AfterFailure],
    *args,
    **kwargs
):
    try:
        return await fn(*args, **kwargs)
    except Exception as e:
        fails += 1
        abandon, delay = retry_policy(fails)

        if abandon:
            raise e

        if after_failure is not None:
            try:
                await await_coro(after_failure(e, fails))
            except Exception as e:
                raise RuntimeError(
                    f'[aioretry] after_failure failed, reason: {e}'
                )

        # `delay` could be 0
        if delay > 0:
            await asyncio.sleep(delay)

        return await perform(
            fails,
            fn,
            retry_policy,
            after_failure,
            *args,
            **kwargs
        )


def get_method(
    target: Union[T, str],
    args: Tuple,
    name: str,
) -> T:
    if type(target) is not str:
        return target

    if len(args) == 0:
        raise RuntimeError(
            f'[aioretry] decorator should be used for instance method if {name} as a str `"{target}"` '
        )

    self = args[0]

    return getattr(self, target)  # type: ignore


def retry(
    retry_policy: ParamRetryPolicy,
    after_failure: Optional[ParamAfterFailure] = None
) -> Callable[[TargetFunction], TargetFunction]:
    def wrapper(fn: TargetFunction) -> TargetFunction:
        async def wrapped(*args, **kwargs):
            return await perform(
                0,
                fn,
                get_method(
                    retry_policy,
                    args,
                    'retry_policy'
                ),
                get_method(
                    after_failure,
                    args,
                    'after_failure'
                ) if after_failure is not None else None,
                *args,
                **kwargs
            )

        return wrapped

    return wrapper
