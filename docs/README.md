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


def example_retry_policy(retries):
    # - It will always retry until succeeded
    # - If fails for the first time, it will retry immediately,
    # - If it fails again,
    #   aioretry will perform a 100ms delay before the second retry,
    #   200ms delay before the 3rd retry,
    #   300ms delay before the 4th retry,
    #   the 5th retry immediately (because the counter has been reset),
    #   100ms delay before the 6th retry,
    #   etc...
    return False, retries * 0.1, retries == 3

wrapped = retry(example_retry_policy)(some_async_method)

asyncio.run(wrapped())
```

### retry(retry_policy, after_failure)(fn)

- **fn** `Callable[[...], Awaitable]` the function to be wrapped. The function should be an async function or normal function returns an awaitable.
- **retry_policy** `RetryPolicy`
- **after_failure?** `Optional[Callable[[Exception, int], None]]`

Returns a wrapped function which accepts the same arguments as `fn` and returns an `Awaitable`.

### RetryPolicy

```py
RetryPolicy = Callable[[int], Tuple[bool, Union[float, int], bool]]
```

Retry policy is used to determine what to do next after the `fn` fails to do some certain thing.

```py
abandon, delay, reset = retry_policy(retries)
```

- `retries` is the counter number of how many times aioretry has retried to perform the function `fn`. If `fn` fails for the first time, then `retries` will be `0`
- If `abandon` is `True`, then aioretry will give up reconnecting, otherwise:
  - aioretry will `asyncio.sleep(delay)` before the next retry.
  - If `reset` is `True`, aioretry will reset the retry counter to `0`

## License

[MIT](LICENSE)
