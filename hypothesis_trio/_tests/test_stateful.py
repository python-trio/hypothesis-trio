from hypothesis_trio.stateful import *  # noqa: F401,F403 (Import to trigger monkeypatch)
from hypothesis.stateful import (
    RuleBasedStateMachine,
    run_state_machine_as_test,
    initialize,
    rule,
    invariant,
)


# Ensure monkeypatching `hypothesis.stateful` for supporting trio doesn't
# impact regular synchronous statemachine
def test_vanilla_stateful_with_monkeypatch():
    class LogEventsRuleBasedStateMachine(RuleBasedStateMachine):
        events = []

        @initialize()
        def initialize(self):
            self.events.append("initialize")

        @invariant(check_during_init=True)
        def invariant_before_init(self):
            self.events.append("invariant_before_init")

        @invariant()
        def invariant(self):
            self.events.append("invariant")

        @rule()
        def rule(self):
            self.events.append("rule")

        def teardown(self):
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
