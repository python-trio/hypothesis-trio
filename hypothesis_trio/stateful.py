# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import trio
from trio.testing import trio_test

try:
    import trio_asyncio
except ImportError:
    trio_asyncio = None

from hypothesis.internal.healthcheck import fail_health_check
from hypothesis.stateful import (
    check_type,
    current_verbosity,
    Verbosity,
    Settings,
    HealthCheck,
    given,
    st,
    current_build_context,
    function_digest,
    multiple,
    STATE_MACHINE_RUN_LABEL,
    SHOULD_CONTINUE_LABEL,
    RuleBasedStateMachine,
    VarReference,
    MultipleResults,
    report,
)

# This is an ugly copy-paste since it's currently no possible to plug a special
# runner into run_state_machine_as_test


def run_custom_state_machine_as_test(state_machine_factory, *, settings=None):
    # https://github.com/HypothesisWorks/hypothesis/blob/6173b2a8783fac5bab3fa478d3a5b0719f93b942/hypothesis-python/src/hypothesis/stateful.py#L103-L121
    # <-------------------> snip !
    if settings is None:
        try:
            settings = state_machine_factory.TestCase.settings
            check_type(Settings, settings, "state_machine_factory.TestCase.settings")
        except AttributeError:
            settings = Settings(deadline=None, suppress_health_check=HealthCheck.all())
    check_type(Settings, settings, "settings")

    @settings
    @given(st.data())
    def run_state_machine(factory, data):
        cd = data.conjecture_data
        machine = factory()
        check_type(RuleBasedStateMachine, machine, "state_machine_factory()")
        cd.hypothesis_runner = machine

        print_steps = (
            current_build_context().is_final or current_verbosity() >= Verbosity.debug
        )
        # <-------------------> snip !

        return machine._custom_runner(cd, print_steps, settings)

    # https://github.com/HypothesisWorks/hypothesis/blob/6173b2a8783fac5bab3fa478d3a5b0719f93b942/hypothesis-python/src/hypothesis/stateful.py#L214-L227
    # <-------------------> snip !
    # Use a machine digest to identify stateful tests in the example database
    run_state_machine.hypothesis.inner_test._hypothesis_internal_add_digest = (
        function_digest(state_machine_factory)
    )
    # Copy some attributes so @seed and @reproduce_failure "just work"
    run_state_machine._hypothesis_internal_use_seed = getattr(
        state_machine_factory, "_hypothesis_internal_use_seed", None
    )
    run_state_machine._hypothesis_internal_use_reproduce_failure = getattr(
        state_machine_factory, "_hypothesis_internal_use_reproduce_failure", None
    )
    run_state_machine._hypothesis_internal_print_given_args = False

    run_state_machine(state_machine_factory)
    # <-------------------> snip !


class TrioRuleBasedStateMachine(RuleBasedStateMachine):
    """Trio compatible version of `hypothesis.stateful.RuleBasedStateMachine`."""

    def __init__(self):
        super().__init__()
        self.__started = False
        self.__clock = None
        self.__instruments = []

    def get_root_nursery(self):
        return getattr(self, "_nursery", None)

    def set_clock(self, clock):
        """Define the clock to use in the trio loop.

        .. note::
            This function can only be used inside the `__init__` method (i.e.
            before the trio loop has been started)
        """
        if self.__started:
            raise RuntimeError("Can only set clock during `__init__`")
        if self.__clock:
            raise RuntimeError("clock already provided")
        self.__clock = clock

    def push_instrument(self, instrument):
        """Add an instrument to use in the trio loop.

        .. note::
            This function can only be used inside the `__init__` method (i.e.
            before the trio loop has been started)
        """
        if self.__started:
            raise RuntimeError("Can only add instrument during `__init__`")
        self.__instruments.append(instrument)

    # Runner logic

    def _custom_runner(self, cd, print_steps, settings):
        async def runner(machine):
            # Second part of the ugly copy-paste - no way around it for the moment
            # https://github.com/HypothesisWorks/hypothesis/blob/6173b2a8783fac5bab3fa478d3a5b0719f93b942/hypothesis-python/src/hypothesis/stateful.py#L122-L212
            # <-------------------> snip !
            try:
                if print_steps:
                    report(f"state = {machine.__class__.__name__}()")
                    report("async def steps():")  # <--- New line !
                await machine.check_invariants(settings)  # <--- Await added !
                max_steps = settings.stateful_step_count
                steps_run = 0

                while True:
                    # We basically always want to run the maximum number of steps,
                    # but need to leave a small probability of terminating early
                    # in order to allow for reducing the number of steps once we
                    # find a failing test case, so we stop with probability of
                    # 2 ** -16 during normal operation but force a stop when we've
                    # generated enough steps.
                    cd.start_example(STATE_MACHINE_RUN_LABEL)
                    if steps_run == 0:
                        cd.draw_bits(16, forced=1)
                    elif steps_run >= max_steps:
                        cd.draw_bits(16, forced=0)
                        break
                    else:
                        # All we really care about is whether this value is zero
                        # or non-zero, so if it's > 1 we discard it and insert a
                        # replacement value after
                        cd.start_example(SHOULD_CONTINUE_LABEL)
                        should_continue_value = cd.draw_bits(16)
                        if should_continue_value > 1:
                            cd.stop_example(discard=True)
                            cd.draw_bits(16, forced=int(bool(should_continue_value)))
                        else:
                            cd.stop_example()
                            if should_continue_value == 0:
                                break
                    steps_run += 1

                    # Choose a rule to run, preferring an initialize rule if there are
                    # any which have not been run yet.
                    if machine._initialize_rules_to_run:
                        init_rules = [
                            st.tuples(
                                st.just(rule), st.fixed_dictionaries(rule.arguments)
                            )
                            for rule in machine._initialize_rules_to_run
                        ]
                        rule, data = cd.draw(st.one_of(init_rules))
                        machine._initialize_rules_to_run.remove(rule)
                    else:
                        rule, data = cd.draw(machine._rules_strategy)

                    # Pretty-print the values this rule was called with *before* calling
                    # _add_result_to_targets, to avoid printing arguments which are also
                    # a return value using the variable name they are assigned to.
                    # See https://github.com/HypothesisWorks/hypothesis/issues/2341
                    if print_steps:
                        data_to_print = {
                            k: machine._pretty_print(v) for k, v in data.items()
                        }

                    # Assign 'result' here in case executing the rule fails below
                    result = multiple()
                    try:
                        data = dict(data)
                        for k, v in list(data.items()):
                            if isinstance(v, VarReference):
                                data[k] = machine.names_to_values[v.name]
                        result = await rule.function(
                            machine, **data
                        )  # <--- Await added !
                        if rule.targets:
                            if isinstance(result, MultipleResults):
                                for single_result in result.values:
                                    machine._add_result_to_targets(
                                        rule.targets, single_result
                                    )
                            else:
                                machine._add_result_to_targets(rule.targets, result)
                        elif result is not None:
                            fail_health_check(
                                settings,
                                "Rules should return None if they have no target bundle, "
                                f"but {rule.function.__qualname__} returned {result!r}",
                                HealthCheck.return_value,
                            )
                    finally:
                        if print_steps:
                            # 'result' is only used if the step has target bundles.
                            # If it does, and the result is a 'MultipleResult',
                            # then 'print_step' prints a multi-variable assignment.
                            machine._print_step(rule, data_to_print, result)
                    await machine.check_invariants(settings)  # <--- Await added !
                    cd.stop_example()
            finally:
                if print_steps:
                    report(
                        "    await state.teardown()"
                    )  # <--- Indentation + await added !
                    report("state.trio_run(steps)")  # <--- New line !
                await machine.teardown()  # <--- Await added !
            # <-------------------> snip !

        self.trio_run(runner, self)

    def _trio_main_afn_factory(self, corofn, *args):
        async def _trio_main_afn(**kwargs):
            async with trio.open_nursery() as self._nursery:
                await corofn(*args)
                self._nursery.cancel_scope.cancel()

        return _trio_main_afn

    def trio_run(self, corofn, *args):
        self.__started = True
        kwargs = {
            "instrument_%s" % i: instrument
            for i, instrument in enumerate(self.__instruments)
        }
        if self.__clock:
            kwargs["clock"] = self.__clock
        trio_test(self._trio_main_afn_factory(corofn, *args))(**kwargs)

    # Async methods

    async def teardown(self):
        """Called after a run has finished executing to clean up any necessary
        state.

        Does nothing by default.
        """
        pass

    # Copy-paste - no way around it for the moment
    # https://github.com/HypothesisWorks/hypothesis/blob/6173b2a8783fac5bab3fa478d3a5b0719f93b942/hypothesis-python/src/hypothesis/stateful.py#L368-L387
    # <-------------------> snip !
    async def check_invariants(self, settings):  # <-- Async added !
        for invar in self.invariants():
            if self._initialize_rules_to_run and not invar.check_during_init:
                continue
            if not all(precond(self) for precond in invar.preconditions):
                continue
            if (
                current_build_context().is_final
                or settings.verbosity >= Verbosity.debug
            ):
                report(f"state.{invar.function.__name__}()")
            result = await invar.function(self)  # <-- Await added !
            if result is not None:
                fail_health_check(
                    settings,
                    "The return value of an @invariant is always ignored, but "
                    f"{invar.function.__qualname__} returned {result!r} "
                    "instead of None",
                    HealthCheck.return_value,
                )

    # <-------------------> snip !

    # Reporting

    # Last part of the ugly copy-paste - no way around it for the moment
    # https://github.com/HypothesisWorks/hypothesis/blob/6173b2a8783fac5bab3fa478d3a5b0719f93b942/hypothesis-python/src/hypothesis/stateful.py#L339-L357
    # <-------------------> snip !
    def _print_step(self, rule, data, result):
        self.step_count = getattr(self, "step_count", 0) + 1
        # If the step has target bundles, and the result is a MultipleResults
        # then we want to assign to multiple variables.
        if isinstance(result, MultipleResults):
            n_output_vars = len(result.values)
        else:
            n_output_vars = 1
        if rule.targets and n_output_vars >= 1:
            output_assignment = ", ".join(self._last_names(n_output_vars)) + " = "
        else:
            output_assignment = ""
        report(
            "    {}await state.{}({})".format(  # <--- Identation+await added !
                output_assignment,
                rule.function.__name__,
                ", ".join("%s=%s" % kv for kv in data.items()),
            )
        )

    # <-------------------> snip !


if trio_asyncio:

    class TrioAsyncioRuleBasedStateMachine(TrioRuleBasedStateMachine):
        def get_asyncio_loop(self):
            return getattr(self, "_loop", None)

        def _trio_main_afn_factory(self, corofn, *args):
            async def _trio_main_afn(**kwargs):
                async with trio_asyncio.open_loop() as self._loop:
                    async with trio.open_nursery() as self._nursery:
                        await corofn(*args)
                        self._nursery.cancel_scope.cancel()

            return _trio_main_afn


# Monkey patching


def monkey_patch_hypothesis():
    import hypothesis.stateful

    if hasattr(hypothesis.stateful, "original_run_state_machine_as_test"):
        return
    original = hypothesis.stateful.run_state_machine_as_test

    def run_state_machine_as_test(state_machine_factory, *, settings=None):
        """Run a state machine definition as a test, either silently doing nothing
        or printing a minimal breaking program and raising an exception.

        state_machine_factory is anything which returns an instance of
        RuleBasedStateMachine when called with no arguments - it can be a class or a
        function. settings will be used to control the execution of the test.
        """
        if hasattr(state_machine_factory, "_custom_runner"):
            return run_custom_state_machine_as_test(
                state_machine_factory, settings=settings
            )
        return original(state_machine_factory, settings=settings)

    hypothesis.stateful.original_run_state_machine_as_test = original
    hypothesis.stateful.run_state_machine_as_test = run_state_machine_as_test


# Monkey patch and expose all objects from original stateful module
monkey_patch_hypothesis()
from hypothesis.stateful import *  # noqa: E402,F401,,F403
