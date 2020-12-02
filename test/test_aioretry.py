import pytest
from datetime import datetime

from aioretry import retry


def retry_policy(fails, _):
    return False, (fails - 1) * 0.1


@pytest.mark.asyncio
async def test_success():
    @retry(retry_policy)
    async def run(n):
        assert n == 1
        return 1

    assert await run(1) == 1


@pytest.mark.asyncio
async def test_success_instance_normal_rp():
    class A:
        n = 1

        @retry(retry_policy)
        async def run(self):
            assert self.n == 1
            return self.n

    assert await A().run() == 1


@pytest.mark.asyncio
async def test_recursive():
    class A:
        n = 0

        def _retry_policy(self, fails, _):
            return False, 0

        @retry('_retry_policy')
        async def run(self):
            self.n += 1

            if self.n < 1000:
                raise RuntimeError('fail')

            return self.n

    assert await A().run() == 1000


@pytest.mark.asyncio
async def test_success_instance_str_rp():
    class A:
        n = 1

        def _retry_policy(self, retries, _):
            return retry_policy(retries, _)

        @retry('_retry_policy')
        async def run(self):
            assert self.n == 1
            return self.n

    assert await A().run() == 1


async def run_retry(async_after_failture: bool):
    errors = []

    if async_after_failture:
        async def before_retry(e, fails):
            errors.append(
                (
                    e,
                    fails,
                    datetime.now()
                )
            )

    else:
        def before_retry(e, fails):
            errors.append(
                (
                    e,
                    fails,
                    datetime.now()
                )
            )

    @retry(retry_policy, before_retry)
    async def run():
        length = len(errors)

        if length == 4:
            return 1

        raise RuntimeError(f'{length}')

    current = datetime.now()

    assert await run() == 1

    primative = [
        (int(str(e)), f)
        for e, f, _ in errors
    ]

    assert primative == [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4)
    ]

    for i, t in enumerate(errors):
        s = t[2]

        delay = max(0, (i - 1) * 0.1)
        delta = (s - current).total_seconds()

        assert delay < delta < delay + 0.1

        current = s


@pytest.mark.asyncio
async def test_error_normal_before_retry():
    await run_retry(False)


@pytest.mark.asyncio
async def test_error_async_before_retry():
    await run_retry(True)


@pytest.mark.asyncio
async def test_error_usage():
    @retry('_retry_policy')
    async def run():
        return 1

    with pytest.raises(
        RuntimeError,
        match='retry_policy as a str `"_retry_policy"`'
    ):
        await run()


@pytest.mark.asyncio
async def test_before_retry_fails():
    fail = True

    def before_retry(e, i):
        if fail:
            raise RuntimeError('boom')

    @retry(retry_policy, before_retry)
    async def run():
        if fail:
            raise RuntimeError('haha')

    with pytest.raises(RuntimeError, match='before_retry failed'):
        await run()


@pytest.mark.asyncio
async def test_abandon():
    def retry_policy(fails, _):
        return fails > 3, fails * 0.1

    fail = True

    @retry(retry_policy)
    async def run():
        if fail:
            raise RuntimeError('boom')

    with pytest.raises(RuntimeError, match='boom'):
        await run()


@pytest.mark.asyncio
async def test_retry_policy_on_exceptions():
    def retry_policy(_, e):
        if isinstance(e, KeyError):
            return True, 0

        return False, 0.1

    class A:
        def __init__(self):
            self._failed = False

        @retry(
            retry_policy=retry_policy
        )
        async def run(self, value_error: bool = False):
            if value_error:
                if self._failed:
                    return 1

                self._failed = True
                raise ValueError('value error')

            raise KeyError('key error')

    a = A()

    assert await a.run(True) == 1

    with pytest.raises(KeyError, match='key error'):
        await a.run()
