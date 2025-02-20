[![](https://github.com/kaelzhang/python-aioretry/actions/workflows/python.yml/badge.svg)](https://github.com/kaelzhang/python-aioretry/actions/workflows/python.yml)
[![](https://codecov.io/gh/kaelzhang/python-aioretry/branch/master/graph/badge.svg)](https://codecov.io/gh/kaelzhang/python-aioretry)
[![](https://img.shields.io/pypi/v/aioretry.svg)](https://pypi.org/project/aioretry/)
[![Conda version](https://img.shields.io/conda/vn/conda-forge/aioretry)](https://anaconda.org/conda-forge/aioretry)
[![](https://img.shields.io/pypi/l/aioretry.svg)](https://github.com/kaelzhang/python-aioretry)

# aioretry

Asyncio retry utility for Python 3.7+

- [Upgrade guide](#upgrade-guide)

## Install

```sh
$ pip install aioretry
```

A [conda-forge recipe](https://github.com/conda-forge/aioretry-feedstock) is also available, so you can also use

```sh
conda install -c conda-forge aioretry
```

## Usage

```py
import asyncio

from aioretry import (
    retry,
    # Tuple[bool, Union[int, float]]
    RetryPolicyStrategy,
    RetryInfo
)

# This example shows the usage with python typings
def retry_policy(info: RetryInfo) -> RetryPolicyStrategy:
    """
    - It will always retry until succeeded: abandon = False
    - If fails for the first time, it will retry immediately,
    - If it fails again,
      aioretry will perform a 100ms delay before the second retry,
      200ms delay before the 3rd retry,
      the 4th retry immediately,
      100ms delay before the 5th retry,
      etc...
    """
    return False, (info.fails - 1) % 3 * 0.1


@retry(retry_policy)
async def connect_to_server():
    # connec to server
    ...

asyncio.run(connect_to_server())
```

### Use as class instance method decorator

We could also use `retry` as a decorator for instance method

```py
class Client:
    @retry(retry_policy)
    async def connect(self):
        await self._connect()

asyncio.run(Client().connect())
```

### Use instance method as retry policy

`retry_policy` could be the method name of the class if `retry` is used as a decorator for instance method.

```py
class ClientWithConfigurableRetryPolicy(Client):
    def __init__(self, max_retries: int = 3):
        self._max_retries = max_retries

    def _retry_policy(self, info: RetryInfo) -> RetryPolicyStrategy:
        return info.fails > self._max_retries, info.fails * 0.1

    # Then aioretry will use `self._retry_policy` as the retry policy.
    # And by using a str as the parameter `retry_policy`,
    # the decorator must be used for instance methods
    @retry('_retry_policy')
    async def connect_with_retry_policy_name(self):
        await self._connect()

    # We should also be able to use a method as the retry policy
    @retry(_retry_policy)
    async def connect_with_method_retry_policy(self):
        await self._connect()


asyncio.run(ClientWithConfigurableRetryPolicy(10).connect())
```

### Register an `before_retry` callback

We could also register an `before_retry` callback which will be executed after every failure of the target function if the corresponding retry is not abandoned.

```py
class ClientTrackableFailures(ClientWithConfigurableRetryPolicy):
    # `before_retry` could either be a sync function or an async function
    async def _before_retry(self, info: RetryInfo) -> None:
        await self._send_failure_log(info.exception, info.fails)

    @retry(
      retry_policy='_retry_policy',

      # Similar to `retry_policy`,
      # `before_retry` could either be a Callable or a str
      before_retry='_before_retry'
    )
    async def connect(self):
        await self._connect()
```

### Only retry for certain types of exceptions

```py
def retry_policy(info: RetryInfo) -> RetryPolicyStrategy:
    if isinstance(info.exception, (KeyError, ValueError)):
        # If it raises a KeyError or a ValueError, it will not retry.
        return True, 0

    # Otherwise, retry immediately
    return False, 0

@retry(retry_policy)
async def foo():
    # do something that might raise KeyError, ValueError or RuntimeError
    ...
```

## APIs

### retry(retry_policy, before_retry)(fn)

- **fn** `Callable[[...], Awaitable]` the function to be wrapped. The function should be an async function or normal function returns an awaitable.
- **retry_policy** `Union[str, RetryPolicy]`
- **before_retry?** `Optional[Union[str, Callable[[RetryInfo], Optional[Awaitable]]]]` If specified, `before_retry` is called after each failure of `fn` and before the corresponding retry. If the retry is abandoned, `before_retry` will not be executed.

Returns a wrapped function which accepts the same arguments as `fn` and returns an `Awaitable`.

### RetryPolicy

```py
RetryPolicyStrategy = Tuple[bool, int | float]
RetryPolicy = Callable[[RetryInfo], RetryPolicyStrategy | Awaitable[RetryPolicyStrategy]]
```

Retry policy is used to determine what to do next after the `fn` fails to do some certain thing.

```py
rt = retry_policy(info)

abandon, delay = (
    # Since 6.2.0, retry_policy could also return an `Awaitable`
    await rt
    if inspect.isawaitable(rt)
    else rt
)
```

- **info** `RetryInfo`
  - **info.fails** `int` is the counter number of how many times function `fn` performs as a failure. If `fn` fails for the first time, then `fails` will be `1`.
  - **info.exception** `Exception` is the exception that `fn` raised.
  - **info.since** `float` is the fractional time seconds generated by [`time.monotonic()`](https://docs.python.org/3/library/time.html#time.monotonic) when the first failure happens.
- If `abandon` is `True`, then aioretry will give up the retry and raise the exception directly, otherwise aioretry will sleep `delay` seconds (`asyncio.sleep(delay)`) before the next retry.

```py
def retry_policy(info: RetryInfo):
    if isinstance(info.exception, KeyError):
        # Just raise exceptions of type KeyError
        return True, 0

    return False, info.fails * 0.1
```

### Python typings

```py
from aioretry import (
    # The type of retry_policy function
    RetryPolicy,
    # The type of the return value of retry_policy function
    RetryPolicyStrategy,
    # The type of before_retry function
    BeforeRetry,
    RetryInfo
)
```

## Upgrade guide

Since `5.0.0`, aioretry introduces `RetryInfo` as the only parameter of `retry_policy` or `before_retry`

### 2.x -> 5.x

2.x

```py
def retry_policy(fails: int):
    """A policy that gives no chances to retry
    """

    return True, 0.1 * fails
```

5.x

```py
def retry_policy(info: RetryInfo):
    return True, 0.1 * info.fails
```

### 3.x -> 5.x

3.x

```py
def before_retry(e: Exception, fails: int):
    ...
```

5.x

```py
# Change the sequence of the parameters
def before_retry(info: RetryInfo):
    info.exception
    info.fails
    ...
```

### 4.x -> 5.x

Since `5.0.0`, both `retry_policy` and `before_retry` have only one parameter of type `RetryInfo` respectively.

### 5.x -> 6.x

Since `6.0.0`, `RetryInfo::since` is a `float` value which is generated by [`time.monotonic()`](https://docs.python.org/3/library/time.html#time.monotonic) and is better for measuring intervals than `datetime`, while in `5.x` `RetryInfo::since` is a `datetime`

```py
# 5.x
from datetime import datetime

def retry_policy(info: RetryInfo) -> RetryPolicyStrategy:
    print('error occurred', (datetime.now() - info.since).total_seconds(), 'seconds ago')

    ...
```

```py
# 6.x
import time

def retry_policy(info: RetryInfo) -> RetryPolicyStrategy:
    print('error occurred', time.monotonic() - info.since, 'seconds ago')

    ...
```

## License

[MIT](LICENSE)
