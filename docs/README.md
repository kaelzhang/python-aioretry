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
from aioretry import retry
import asyncio


def example_retry_policy(fails):
    # - It will always retry until succeeded
    # - If fails for the first time, it will retry immediately,
    # - If it fails again,
    #   aioretry will perform a 100ms delay before the second retry,
    #   200ms delay before the 3rd retry,
    #   the 4th retry immediately,
    #   100ms delay before the 5th retry,
    #   etc...
    return False, (fails - 1) % 3 * 0.1


@retry(example_retry_policy)
async def connect_to_server():
    # connec to server
    ...

asyncio.run(connect_to_server())
```

### Use as class instance method decorator

```py
class
```

### retry(retry_policy, after_failure)(fn)

- **fn** `Callable[[...], Awaitable]` the function to be wrapped. The function should be an async function or normal function returns an awaitable.
- **retry_policy** `Union[str, RetryPolicy]`
- **after_failure?** `Optional[Union[str, Callable[[Exception, int], Optional[Awaitable]]]]` IF specified, `after_failure` is called after each failture of `fn` and before the corresponding retry. If the retry is abandoned, `after_failture` will not be executed.

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
- If `abandon` is `True`, then aioretry will give up reconnecting, otherwise aioretry will `asyncio.sleep(delay)` before the next retry.

## License

[MIT](LICENSE)
