import pytest
import trio
from trio.abc import Instrument
from trio.testing import MockClock

from hypothesis_trio.stateful import TrioGenericStateMachine, TrioRuleBasedStateMachine
from hypothesis.stateful import initialize, rule, invariant, run_state_machine_as_test
from hypothesis.strategies import just, integers, lists, tuples


def test_triggers():
    class LogEventsStateMachine(TrioGenericStateMachine):
        events = []

        async def teardown(self):
            await trio.sleep(0)
            self.events.append('teardown')

        def steps(self):
            return just(42)

        async def execute_step(self, step):
            await trio.sleep(0)
            assert step is 42
            self.events.append('execute_step')

        async def check_invariants(self):
            await trio.sleep(0)
            self.events.append('check_invariants')

    run_state_machine_as_test(LogEventsStateMachine)

    per_run_events = []
    current_run_events = []
    for event in LogEventsStateMachine.events:
        current_run_events.append(event)
        if event == 'teardown':
            per_run_events.append(current_run_events)
            current_run_events = []

    for run_events in per_run_events:
        expected_events = ['check_invariants']
        expected_events += ['execute_step', 'check_invariants'
                            ] * ((len(run_events) - 2) // 2)
        expected_events.append('teardown')
        assert run_events == expected_events


def test_rule_based():
    class LogEventsRuleBasedStateMachine(TrioRuleBasedStateMachine):
        events = []

        @initialize()
        async def initialize(self):
            await trio.sleep(0)
            self.events.append('initialize')

        @invariant()
        async def invariant(self):
            await trio.sleep(0)
            self.events.append('invariant')

        @rule()
        async def rule(self):
            await trio.sleep(0)
            self.events.append('rule')

        async def teardown(self):
            await trio.sleep(0)
            self.events.append('teardown')

    run_state_machine_as_test(LogEventsRuleBasedStateMachine)

    per_run_events = []
    current_run_events = []
    for event in LogEventsRuleBasedStateMachine.events:
        current_run_events.append(event)
        if event == 'teardown':
            per_run_events.append(current_run_events)
            current_run_events = []

    for run_events in per_run_events:
        expected_events = ['invariant', 'initialize', 'invariant']
        expected_events += ['rule', 'invariant'] * ((len(run_events) - 3) // 2)
        expected_events.append('teardown')
        assert run_events == expected_events


def test_custom_clock_and_instruments():
    class CustomMockClock(MockClock):
        def __init__(self):
            super().__init__()
            self.in_use = False

        def start_clock(self):
            self.in_use = True

    class CustomInstrument(Instrument):
        def __init__(self):
            super().__init__()
            self.in_use = False

        def before_run(self):
            self.in_use = True

    class CustomClockStateMachine(TrioRuleBasedStateMachine):
        def __init__(self):
            super().__init__()

            self.expected_clock = CustomMockClock()
            self.set_clock(self.expected_clock)

            self.expected_instruments = [CustomInstrument() for _ in range(3)]
            for instrument in self.expected_instruments:
                self.push_instrument(instrument)

        @rule()
        async def rule(self):
            assert self.expected_clock.in_use
            for instrument in self.expected_instruments:
                assert instrument.in_use

    run_state_machine_as_test(CustomClockStateMachine)


def test_cannot_customize_clock_and_instruments_after_start():
    class BadTimeForCustomizingStateMachine(TrioRuleBasedStateMachine):
        def _try_customizing(self):
            with pytest.raises(RuntimeError):
                self.set_clock(MockClock())
            with pytest.raises(RuntimeError):
                self.push_instrument(Instrument())

        @initialize()
        async def initialize(self):
            self._try_customizing()

        @invariant()
        async def invariant(self):
            self._try_customizing()

        @rule()
        async def rule(self):
            self._try_customizing()

        async def teardown(self):
            self._try_customizing()

    run_state_machine_as_test(BadTimeForCustomizingStateMachine)


def test_trio_style():
    async def _consumer(
        in_queue, out_queue, *, task_status=trio.TASK_STATUS_IGNORED
    ):
        with trio.open_cancel_scope() as cancel_scope:
            task_status.started(cancel_scope)
            while True:
                x, y = await in_queue.get()
                await trio.sleep(0)
                result = x + y
                await out_queue.put('%s + %s = %s' % (x, y, result))

    class TrioStyleStateMachine(TrioRuleBasedStateMachine):
        @initialize()
        async def initialize(self):
            self.job_queue = trio.Queue(100)
            self.result_queue = trio.Queue(100)
            self.consumer_cancel_scope = await self.get_root_nursery().start(
                _consumer, self.job_queue, self.result_queue
            )

        @rule(work=lists(tuples(integers(), integers())))
        async def generate_work(self, work):
            await trio.sleep(0)
            for x, y in work:
                await self.job_queue.put((x, y))

        @rule()
        async def restart_consumer(self):
            self.consumer_cancel_scope.cancel()
            self.consumer_cancel_scope = await self.get_root_nursery().start(
                _consumer, self.job_queue, self.result_queue
            )

        @invariant()
        async def check_results(self):
            while True:
                try:
                    job = self.result_queue.get_nowait()
                    assert isinstance(job, str)
                except (trio.WouldBlock, AttributeError):
                    break

    run_state_machine_as_test(TrioStyleStateMachine)
