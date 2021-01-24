[![](https://travis-ci.org/kaelzhang/python-aioretry.svg?branch=master)](https://travis-ci.org/kaelzhang/python-aioretry)
[![](https://codecov.io/gh/kaelzhang/python-aioretry/branch/master/graph/badge.svg)](https://codecov.io/gh/kaelzhang/python-aioretry)
[![](https://img.shields.io/pypi/v/aioretry.svg)](https://pypi.org/project/aioretry/)
[![](https://img.shields.io/pypi/l/aioretry.svg)](https://github.com/kaelzhang/python-aioretry)

# aioretry

Asyncio retry utility for Python 3.7+

- [Upgrade guide](#upgrade-guide)

## Install

```sh
$ pip install aioretry
```

## Usage

```py
import asyncio
from typing import (
  Tuple
)

from aioretry import retry


def retry_policy(fails: int, _: Exception) -> Tuple[bool, float]:
    """The second parameter of `retry_policy` is the exception,
    which we will not use in this simple example.

    - It will always retry until succeeded
    - If fails for the first time, it will retry immediately,
    - If it fails again,
      aioretry will perform a 100ms delay before the second retry,
      200ms delay before the 3rd retry,
      the 4th retry immediately,
      100ms delay before the 5th retry,
      etc...
    """
    return False, (fails - 1) % 3 * 0.1


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

    def _retry_policy(self, fails: int) -> Tuple[bool, float]:
        return fails > self._max_retries, fails * 0.1

    # Then aioretry will use `self._retry_policy` as the retry policy.
    # And by using a str as the parameter `retry_policy`,
    # the decorator must be used for instance methods
    @retry('_retry_policy')
    async def connect(self):
        await self._connect()

asyncio.run(ClientWithConfigurableRetryPolicy(10).connect())
```

### Register an `before_retry` callback

We could also register an `before_retry` callback which will be executed after every failure of the target function if the corresponding retry is not abandoned.

```py
class ClientTrackableFailures(ClientWithConfigurableRetryPolicy):
    # `before_retry` could either be a sync function or an async function
    async def _before_retry(self, error: Exception, fails: int) -> None:
        await self._send_failure_log(error, fails)

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

@retry(
    retry_policy=retry_policy,
    # If it raises a RuntimeError, it will not retry.
    on_exceptions=(KeyError, ValueError)
)
async def foo():
    # do something that might raise KeyError, ValueError or RuntimeError
    ...
```

## APIs

### retry(retry_policy, before_retry)(fn)

- **fn** `Callable[[...], Awaitable]` the function to be wrapped. The function should be an async function or normal function returns an awaitable.
- **retry_policy** `Union[str, RetryPolicy]`
- **before_retry?** `Optional[Union[str, Callable[[Exception, int], Optional[Awaitable]]]]` If specified, `before_retry` is called after each failture of `fn` and before the corresponding retry. If the retry is abandoned, `before_retry` will not be executed.

Returns a wrapped function which accepts the same arguments as `fn` and returns an `Awaitable`.

### RetryPolicy

```py
RetryPolicy = Callable[[int, Exception], Tuple[bool, Union[float, int]]]
```

Retry policy is used to determine what to do next after the `fn` fails to do some certain thing.

```py
abandon, delay = retry_policy(fails, exception)
```

- `fails` is the counter number of how many times function `fn` performs as a failure. If `fn` fails for the first time, then `fails` will be `1`
- `exception` is the exception that `fn` raised
- If `abandon` is `True`, then aioretry will give up the retry and raise the exception directly, otherwise aioretry will sleep `delay` seconds (`asyncio.sleep(delay)`) before the next retry.

```py
def retry_policy(fails, exception):
    if isinstance(exception, KeyError):
        # Just raise exceptions of type KeyError
        return True, 0

    return False, fails * 0.1
```

## Upgrade guide

### 2.x -> 3.x

Since `3.0.0`, aioretry introduces a second positional parameter of type `Exception` for `retry_policy` while the function of `2.x` only has one parameters.

2.x

```py
def retry_policy(fails: int):
    """A policy that gives no chances to retry
    """

    return True, 0
```

3.x

```py
def retry_policy(fails, int, _: Exception):
    return True, 0
```

## License

[MIT](LICENSE)
