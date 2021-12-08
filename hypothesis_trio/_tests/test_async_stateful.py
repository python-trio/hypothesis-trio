import pytest
import trio
from trio.abc import Instrument
from trio.testing import MockClock

import hypothesis
from hypothesis_trio.stateful import TrioRuleBasedStateMachine
from hypothesis.stateful import (
    Bundle,
    initialize,
    rule,
    invariant,
    run_state_machine_as_test,
    multiple,
)
from hypothesis.strategies import integers, lists, tuples


def test_rule_based():
    class LogEventsRuleBasedStateMachine(TrioRuleBasedStateMachine):
        events = []

        @initialize()
        async def initialize(self):
            await trio.sleep(0)
            self.events.append("initialize")

        @invariant(check_during_init=True)
        async def invariant_before_init(self):
            await trio.sleep(0)
            self.events.append("invariant_before_init")

        @invariant()
        async def invariant(self):
            await trio.sleep(0)
            self.events.append("invariant")

        @rule()
        async def rule(self):
            await trio.sleep(0)
            self.events.append("rule")

        async def teardown(self):
            await trio.sleep(0)
            self.events.append("teardown")

    run_state_machine_as_test(LogEventsRuleBasedStateMachine)

    per_run_events = []
    current_run_events = []
    for event in LogEventsRuleBasedStateMachine.events:
        current_run_events.append(event)
        if event == "teardown":
            per_run_events.append(current_run_events)
            current_run_events = []

    for run_events in per_run_events:
        expected_events = [
            "invariant_before_init",
            "initialize",
            "invariant",
            "invariant_before_init",
        ]
        expected_events += ["rule", "invariant", "invariant_before_init"] * (
            (len(run_events) - 4) // 3
        )
        expected_events.append("teardown")
        assert run_events == expected_events


def test_custom_clock_and_instruments(monkeypatch):
    # Subclassing MockClock is dissallowed since v0.15.0,
    # but it ain't gonna stop us from checking it is correctly used !
    custom_clock_used = False
    vanilla_start_clock = MockClock.start_clock

    def patched_start_clock(self, *args, **kwargs):
        nonlocal custom_clock_used
        custom_clock_used = True
        vanilla_start_clock(self, *args, **kwargs)

    monkeypatch.setattr(MockClock, "start_clock", patched_start_clock)

    class CustomInstrument(Instrument):
        def __init__(self):
            super().__init__()
            self.in_use = False

        def before_run(self):
            self.in_use = True

    class CustomClockStateMachine(TrioRuleBasedStateMachine):
        def __init__(self):
            super().__init__()

            self.expected_clock = MockClock()
            self.set_clock(self.expected_clock)

            self.expected_instruments = [CustomInstrument() for _ in range(3)]
            for instrument in self.expected_instruments:
                self.push_instrument(instrument)

        @rule()
        async def rule(self):
            assert custom_clock_used
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
    async def consumer(
        receive_job, send_result, *, task_status=trio.TASK_STATUS_IGNORED
    ):
        with trio.CancelScope() as cancel_scope:
            task_status.started(cancel_scope)
            async for x, y in receive_job:
                await trio.sleep(0)
                result = x + y
                await send_result.send("%s + %s = %s" % (x, y, result))

    class TrioStyleStateMachine(TrioRuleBasedStateMachine):
        @initialize()
        async def initialize(self):
            self.send_job, receive_job = trio.open_memory_channel(100)
            send_result, self.receive_result = trio.open_memory_channel(100)
            self.consumer_args = consumer, receive_job, send_result
            self.consumer_cancel_scope = await self.get_root_nursery().start(
                *self.consumer_args
            )

        @rule(work=lists(tuples(integers(), integers())))
        async def generate_work(self, work):
            await trio.sleep(0)
            for x, y in work:
                await self.send_job.send((x, y))

        @rule()
        async def restart_consumer(self):
            self.consumer_cancel_scope.cancel()
            self.consumer_cancel_scope = await self.get_root_nursery().start(
                *self.consumer_args
            )

        @invariant()
        async def check_results(self):
            while True:
                try:
                    job = self.receive_result.receive_nowait()
                    assert isinstance(job, str)
                except (trio.WouldBlock, AttributeError):
                    break

    run_state_machine_as_test(TrioStyleStateMachine)


def test_trio_style_failing_state_machine_with_single_result(capsys):

    # Failing state machine

    class TrioStyleStateMachine(TrioRuleBasedStateMachine):
        Values = Bundle("value")

        @initialize(target=Values)
        async def initialize(self):
            return 1

        @rule(value=Values)
        async def do_work(self, value):
            assert value == 2

    # Check failure

    with pytest.raises(AssertionError) as record:
        run_state_machine_as_test(TrioStyleStateMachine)
    captured = capsys.readouterr()
    assert "assert 1 == 2" in str(record.value)

    # Check steps

    with pytest.raises(AssertionError) as record:
        state = TrioStyleStateMachine()

        async def steps():
            v1 = await state.initialize()
            await state.do_work(value=v1)
            await state.teardown()

        state.trio_run(steps)
    assert "assert 1 == 2" in str(record.value)

    # Check steps printout
    assert (
        """\
state = TrioStyleStateMachine()
async def steps():
    v1 = await state.initialize()
    await state.do_work(value=v1)
    await state.teardown()
state.trio_run(steps)
"""
        in captured.out
    ), captured.out


def test_trio_style_failing_state_machine_with_multiple_result(capsys):

    # Failing state machine

    class TrioStyleStateMachine(TrioRuleBasedStateMachine):
        Values = Bundle("value")

        @initialize(target=Values)
        async def initialize(self):
            return multiple(1, 2)

        @rule(value=Values)
        async def do_work(self, value):
            assert value == 2

    # Check failure

    with pytest.raises(AssertionError) as record:
        run_state_machine_as_test(TrioStyleStateMachine)
    captured = capsys.readouterr()
    assert "assert 1 == 2" in str(record.value)

    # Check steps

    with pytest.raises(AssertionError) as record:
        state = TrioStyleStateMachine()

        async def steps():
            v1, v2 = await state.initialize()
            await state.do_work(value=v1)
            await state.teardown()

        state.trio_run(steps)
    assert "assert 1 == 2" in str(record.value)

    # Check steps printout
    assert (
        """\
state = TrioStyleStateMachine()
async def steps():
    v1, v2 = await state.initialize()
    await state.do_work(value=v1)
    await state.teardown()
state.trio_run(steps)
"""
        in captured.out
    ), captured.out


def test_invalid_state_machine():
    class NotAStateMachine:
        pass

    with pytest.raises(hypothesis.errors.InvalidArgument):
        run_state_machine_as_test(NotAStateMachine)
