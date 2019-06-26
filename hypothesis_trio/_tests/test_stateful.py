from hypothesis_trio.stateful import *  # Import to trigger monkeypatch
from hypothesis.stateful import RuleBasedStateMachine, run_state_machine_as_test, initialize, rule, invariant
from hypothesis.strategies import just


def test_vanilla_stateful_with_monkeypatch():
    class LogEventsStateMachine(RuleBasedStateMachine):
        events = []

        @initialize()
        def init(self):
            self.events.append('init')

        def teardown(self):
            self.events.append('teardown')

        @rule(arg=just(42))
        def step(self, arg):
            assert arg is 42
            self.events.append('execute_step')

        @invariant()
        def check_invariants(self):
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
        expected_events = ['check_invariants', 'init', 'check_invariants']
        expected_events += ['execute_step', 'check_invariants'
                            ] * ((len(run_events) - 4) // 2)
        expected_events.append('teardown')
        assert run_events == expected_events
