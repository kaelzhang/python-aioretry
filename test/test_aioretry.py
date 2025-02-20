import pytest
from time import monotonic

from aioretry import (
    retry
)


def retry_policy(info):
    return False, (info.fails - 1) * 0.1


async def async_retry_policy(info):
    return retry_policy(info)


class AwaitableRetryPolicy:
    def __init__(self, info):
        self._info = info

    def __await__(self):
        yield
        return retry_policy(self._info)


def awaitable_retry_policy(info):
    return AwaitableRetryPolicy(info)


@pytest.mark.asyncio
async def test_simple():
    async def just_return(n = 0):
        return n + 1

    assert await just_return() == 1

    retried = retry(retry_policy)(just_return)
    assert await retried() == 1
    assert await retried(1) == 2

    retried = retry(async_retry_policy)(just_return)
    assert await retried() == 1
    assert await retried(1) == 2

    retried = retry(awaitable_retry_policy)(just_return)
    assert await retried() == 1
    assert await retried(1) == 2

    class FailOnce:
        def __init__(self, policy):
            self._failed = False
            self._policy = policy

        @retry('_policy')
        async def run(self):
            if self._failed:
                return 1

            self._failed = True
            raise RuntimeError('fail')

    assert await FailOnce(retry_policy).run() == 1
    assert await FailOnce(async_retry_policy).run() == 1
    assert await FailOnce(awaitable_retry_policy).run() == 1


@pytest.mark.asyncio
async def test_instance_method():

    @classmethod
    def external_class_retry(cls, info):
        if cls is not FailOnce:
            return True, 0

        return False, (info.fails - 1) * 0.1

    @staticmethod
    def external_static_retry(info):
        return False, (info.fails - 1) * 0.1


    def external_retry(info):
        return False, (info.fails - 1) * 0.1

    def fake_external_retry(_):
        # which should not be used
        return True, 0

    class FailOnce:
        _failed = False
        _isclass = True

        def __init__(self):
            self.external_retry = fake_external_retry

        def _retry(self, info):
            if not self._isclass:
                return True, 0

            return False, (info.fails - 1) * 0.1

        @classmethod
        def _retry_class(cls, info):
            if cls is not FailOnce:
                return True, 0

            return False, (info.fails - 1) * 0.1

        @staticmethod
        def _retry_static(info):
            return False, (info.fails - 1) * 0.1

        @retry(_retry)
        async def run(self):
            return await self._run()

        @retry('_retry')
        async def run_str(self):
            return await self._run()

        @retry(_retry_class)
        async def run_class(self):
            return await self._run()

        @retry('_retry_class')
        async def run_str_class(self):
            return await self._run()

        @retry(_retry_static)
        async def run_static(self):
            return await self._run()

        @retry('_retry_static')
        async def run_str_static(self):
            return await self._run()

        @retry(external_class_retry)
        async def run_external_class(self):
            return await self._run()

        @retry(external_static_retry)
        async def run_external_static(self):
            return await self._run()

        @retry(external_retry)
        async def run_external(self):
            return await self._run()

        async def _run(self):
            if self._failed:
                return 1

            self._failed = True
            raise RuntimeError('fail')

    assert await FailOnce().run() == 1
    assert await FailOnce().run_str() == 1
    assert await FailOnce().run_class() == 1
    assert await FailOnce().run_str_class() == 1
    assert await FailOnce().run_static() == 1
    assert await FailOnce().run_str_static() == 1
    assert await FailOnce().run_external_class() == 1
    assert await FailOnce().run_external_static() == 1

    # It should not use the self.external_retry
    assert await FailOnce().run_external() == 1


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

        def _retry_policy(self, info):
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

        def _retry_policy(self, info):
            return retry_policy(info)

        @retry('_retry_policy')
        async def run(self):
            assert self.n == 1
            return self.n

    assert await A().run() == 1


async def run_retry(async_after_failture: bool):
    errors = []

    if async_after_failture:
        async def before_retry(info):
            errors.append(
                (
                    info,
                    monotonic()
                )
            )

    else:
        def before_retry(info):
            errors.append(
                (
                    info,
                    monotonic()
                )
            )

    @retry(retry_policy, before_retry)
    async def run():
        length = len(errors)

        if length == 4:
            return 1

        raise RuntimeError(f'{length}')

    current = monotonic()

    assert await run() == 1

    primative = [
        (int(str(info.exception)), info.fails)
        for info, _ in errors
    ]

    assert primative == [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4)
    ]

    since = None

    for i, t in enumerate(errors):
        info, time = t

        if since is None:
            since = info.since
            assert current < since < current + 0.1
        else:
            assert since == info.since

        delay = max(0, (i - 1) * 0.1)
        delta = time - current

        assert delay < delta < delay + 0.1

        current = time


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
        match='retry_policy as a str "_retry_policy"'
    ):
        await run()


@pytest.mark.asyncio
async def test_before_retry_fails():
    fail = True

    def before_retry(info):
        if fail:
            raise RuntimeError('boom')

    @retry(retry_policy, before_retry)
    async def run():
        if fail:
            raise RuntimeError('haha')

    with pytest.warns(UserWarning, match='fix'):
        with pytest.raises(RuntimeError, match='boom'):
            await run()


@pytest.mark.asyncio
async def test_abandon():
    def retry_policy(info):
        return info.fails > 3, info.fails * 0.1

    fail = True

    @retry(retry_policy)
    async def run():
        if fail:
            raise RuntimeError('boom')

    with pytest.raises(RuntimeError, match='boom'):
        await run()


@pytest.mark.asyncio
async def test_retry_policy_on_exceptions():
    def retry_policy(info):
        if isinstance(info.exception, KeyError):
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


@pytest.mark.asyncio
async def test_retry_policy_raises():
    def retry_policy():
        return False, 0

    @retry(retry_policy)
    async def run():
        raise RuntimeError('boom')

    with pytest.warns(UserWarning, match='fix'):
        with pytest.raises(TypeError, match='but 1 was given'):
            await run()
