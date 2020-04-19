[![](https://travis-ci.org/kaelzhang/python-aioretry.svg?branch=master)](https://travis-ci.org/kaelzhang/python-aioretry)
[![](https://codecov.io/gh/kaelzhang/python-aioretry/branch/master/graph/badge.svg)](https://codecov.io/gh/kaelzhang/python-aioretry)
[![](https://img.shields.io/pypi/v/aioretry.svg)](https://pypi.org/project/aioretry/)
[![](https://img.shields.io/pypi/l/aioretry.svg)](https://github.com/kaelzhang/python-aioretry)

# aioretry

Asyncio retry utility for Python 3.7+

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


def retry_policy(fails: int) -> Tuple[bool, float]:
    # - It will always retry until succeeded
    # - If fails for the first time, it will retry immediately,
    # - If it fails again,
    #   aioretry will perform a 100ms delay before the second retry,
    #   200ms delay before the 3rd retry,
    #   the 4th retry immediately,
    #   100ms delay before the 5th retry,
    #   etc...
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

### Register an `after_failure` callback

We could also register an `after_failure` callback which will be executed after every failure of the target function if the corresponding retry is not abandoned.

```py
class ClientTrackableFailures(ClientWithConfigurableRetryPolicy):
    # `after_failure` could either be a sync function or an async function
    async def _on_failure(self, error: Exception, fails: int) -> None:
        await self._send_failure_log(error, fails)

    @retry(
      retry_policy='_retry_policy',

      # Similar to `retry_policy`,
      # `after_failure` could either be a Callable or a str
      after_failure='_on_failture'
    )
    async def connect(self):
        await self._connect()
```


## APIs

### retry(retry_policy, after_failure)(fn)

- **fn** `Callable[[...], Awaitable]` the function to be wrapped. The function should be an async function or normal function returns an awaitable.
- **retry_policy** `Union[str, RetryPolicy]`
- **after_failure?** `Optional[Union[str, Callable[[Exception, int], Optional[Awaitable]]]]` If specified, `after_failure` is called after each failture of `fn` and before the corresponding retry. If the retry is abandoned, `after_failture` will not be executed.

Returns a wrapped function which accepts the same arguments as `fn` and returns an `Awaitable`.

### RetryPolicy

```py
RetryPolicy = Callable[[int], Tuple[bool, Union[float, int]]]
```

Retry policy is used to determine what to do next after the `fn` fails to do some certain thing.

```py
abandon, delay = retry_policy(retries)
```

- `fails` is the counter number of how many times function `fn` performs as a failure. If `fn` fails for the first time, then `fails` will be `1`
- If `abandon` is `True`, then aioretry will give up the retry and raise the exception directly, otherwise aioretry will sleep `delay` seconds (`asyncio.sleep(delay)`) before the next retry.

## License

[MIT](LICENSE)
