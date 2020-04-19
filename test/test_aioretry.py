import pytest
from datetime import datetime

from aioretry import retry


def retry_policy(fails):
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
async def test_success_instance_str_rp():
    class A:
        n = 1

        def _retry_policy(self, retries):
            return retry_policy(retries)

        @retry('_retry_policy')
        async def run(self):
            assert self.n == 1
            return self.n

    assert await A().run() == 1


async def run_retry(async_after_failture: bool):
    errors = []

    if async_after_failture:
        async def after_failure(e, fails):
            errors.append(
                (
                    e,
                    fails,
                    datetime.now()
                )
            )

    else:
        def after_failure(e, fails):
            errors.append(
                (
                    e,
                    fails,
                    datetime.now()
                )
            )

    @retry(retry_policy, after_failure)
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
async def test_error_normal_after_failure():
    await run_retry(False)


@pytest.mark.asyncio
async def test_error_async_after_failure():
    await run_retry(True)


@pytest.mark.asyncio
async def test_error_usage():
    @retry('_retry_policy')
    async def run():
        return 1

    with pytest.raises(RuntimeError, match=f'retry_policy as a str `"_retry_policy"`'):
        await run()


@pytest.mark.asyncio
async def test_after_failure_fails():
    fail = True

    def after_failure(e, i):
        if fail:
            raise RuntimeError('boom')

    @retry(retry_policy, after_failure)
    async def run():
        if fail:
            raise RuntimeError('haha')

    with pytest.raises(RuntimeError, match='after_failure failed'):
        await run()


@pytest.mark.asyncio
async def test_abandon():
    def retry_policy(fails):
        return fails > 3, fails * 0.1

    fail = True

    @retry(retry_policy)
    async def run():
        if fail:
            raise RuntimeError('boom')

    with pytest.raises(RuntimeError, match='boom'):
        await run()
