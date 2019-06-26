import trio_asyncio
import asyncio

from hypothesis_trio.stateful import TrioAsyncioRuleBasedStateMachine
from hypothesis.stateful import initialize, rule, invariant, run_state_machine_as_test


def test_access_asyncio_loop():
    class LogEventsRuleBasedStateMachine(TrioAsyncioRuleBasedStateMachine):
        async def _check_asyncio_loop(self):
            assert self.get_asyncio_loop() == asyncio.get_event_loop()
            await trio_asyncio.aio_as_trio(lambda: asyncio.sleep(0))

        @initialize()
        async def initialize(self):
            await self._check_asyncio_loop()

        @invariant()
        async def invariant(self):
            await self._check_asyncio_loop()

        @rule()
        async def rule(self):
            await self._check_asyncio_loop()

        async def teardown(self):
            await self._check_asyncio_loop()

    run_state_machine_as_test(LogEventsRuleBasedStateMachine)
