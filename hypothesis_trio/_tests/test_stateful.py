from hypothesis_trio.stateful import *  # Import to trigger monkeypatch
from hypothesis.stateful import GenericStateMachine, run_state_machine_as_test
from hypothesis.strategies import just


def test_vanilla_stateful_with_monkeypatch():
    class LogEventsStateMachine(GenericStateMachine):
        events = []

        def teardown(self):
            self.events.append('teardown')

        def steps(self):
            return just(42)

        def execute_step(self, step):
            assert step is 42
            self.events.append('execute_step')

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
        expected_events = ['check_invariants']
        expected_events += ['execute_step', 'check_invariants'
                            ] * ((len(run_events) - 2) // 2)
        expected_events.append('teardown')
        assert run_events == expected_events
