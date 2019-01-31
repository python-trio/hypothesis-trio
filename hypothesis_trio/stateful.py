import trio
from trio.testing import trio_test


from hypothesis.stateful import (
    # Needed for run_state_machine_as_test copy-paste
    check_type,
    cu,
    current_verbosity,
    Verbosity,
    Settings,
    HealthCheck,
    GenericStateMachine,
    given,
    st,
    current_build_context,
    function_digest,
    # Needed for TrioRuleBasedStateMachine
    RuleBasedStateMachine,
    VarReference,
    MultipleResults,
)


# This is an ugly copy-paste since it's currently no possible to plug a special
# runner into run_state_machine_as_test

def run_state_machine_as_test(state_machine_factory, settings=None):
    """Run a state machine definition as a test, either silently doing nothing
    or printing a minimal breaking program and raising an exception.
    state_machine_factory is anything which returns an instance of
    GenericStateMachine when called with no arguments - it can be a class or a
    function. settings will be used to control the execution of the test.
    """
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
        machine = factory()
        check_type(GenericStateMachine, machine, "state_machine_factory()")
        data.conjecture_data.hypothesis_runner = machine

        n_steps = settings.stateful_step_count
        should_continue = cu.many(
            data.conjecture_data, min_size=1, max_size=n_steps, average_size=n_steps
        )

        print_steps = (
            current_build_context().is_final or current_verbosity() >= Verbosity.debug
        )

        # Plug a custom machinery
        # This block is not in the original copy-paste
        try:
            machine._custom_runner
        except AttributeError:
            pass
        else:
            return machine._custom_runner(data, print_steps, should_continue)

        try:
            if print_steps:
                machine.print_start()
            machine.check_invariants()

            while should_continue.more():
                value = data.conjecture_data.draw(machine.steps())
                if print_steps:
                    machine.print_step(value)
                machine.execute_step(value)
                machine.check_invariants()
        finally:
            if print_steps:
                machine.print_end()
            machine.teardown()

    # Use a machine digest to identify stateful tests in the example database
    run_state_machine.hypothesis.inner_test._hypothesis_internal_add_digest = function_digest(
        state_machine_factory
    )
    # Copy some attributes so @seed and @reproduce_failure "just work"
    run_state_machine._hypothesis_internal_use_seed = getattr(
        state_machine_factory, "_hypothesis_internal_use_seed", None
    )
    run_state_machine._hypothesis_internal_use_reproduce_failure = getattr(
        state_machine_factory, "_hypothesis_internal_use_reproduce_failure", None
    )

    run_state_machine(state_machine_factory)


class TrioGenericStateMachine(GenericStateMachine):
    """Trio compatible version of `hypothesis.stateful.GenericStateMachine`
    """

    def __init__(self):
        super().__init__()
        self.__started = False
        self.__clock = None
        self.__instruments = []

    def get_root_nursery(self):
        return getattr(self, '_nursery', None)

    def set_clock(self, clock):
        """Define the clock to use in the trio loop.

        .. note::
            This function can only be used inside the `__init__` method (i.e.
            before the trio loop has been started)
        """
        if self.__started:
            raise RuntimeError('Can only set clock during `__init__`')
        if self.__clock:
            raise RuntimeError('clock already provided')
        self.__clock = clock

    def push_instrument(self, instrument):
        """Add an instrument to use in the trio loop.

        .. note::
            This function can only be used inside the `__init__` method (i.e.
            before the trio loop has been started)
        """
        if self.__started:
            raise RuntimeError('Can only add instrument during `__init__`')
        self.__instruments.append(instrument)

    def _custom_runner(self, data, print_steps, should_continue):
        async def _run(**kwargs):
            async with trio.open_nursery() as self._nursery:
                try:
                    if print_steps:
                        self.print_start()
                    await self.check_invariants()

                    while should_continue.more():
                        value = data.conjecture_data.draw(self.steps())
                        if print_steps:
                            self.print_step(value)
                        await self.execute_step(value)
                        await self.check_invariants()
                finally:
                    if print_steps:
                        self.print_end()
                    await self.teardown()
                    self._nursery.cancel_scope.cancel()

        self.__started = True
        kwargs = {
            'instrument_%s' % i: instrument
            for i, instrument in enumerate(self.__instruments)
        }
        if self.__clock:
            kwargs['clock'] = self.__clock
        trio_test(_run)(**kwargs)

    async def execute_step(self, step):
        """Execute a step that has been previously drawn from self.steps()"""
        raise NotImplementedError(u'%r.execute_step()' % (self,))

    async def teardown(self):
        """Called after a run has finished executing to clean up any necessary
        state.

        Does nothing by default.
        """
        pass

    async def check_invariants(self):
        """Called after initializing and after executing each step."""
        pass


class TrioRuleBasedStateMachine(TrioGenericStateMachine,
                                RuleBasedStateMachine):
    """Trio compatible version of `hypothesis.stateful.RuleBasedStateMachine`.
    """

    async def execute_step(self, step):
        rule, data = step
        data = dict(data)
        for k, v in list(data.items()):
            if isinstance(v, VarReference):
                data[k] = self.names_to_values[v.name]
        result = await rule.function(self, **data)
        if rule.targets:
            if isinstance(result, MultipleResults):
                for single_result in result.values:
                    self._add_result_to_targets(rule.targets, single_result)
            else:
                self._add_result_to_targets(rule.targets, result)
        if self._initialize_rules_to_run:
            self._initialize_rules_to_run.remove(rule)

    async def check_invariants(self):
        for invar in self.invariants():
            if invar.precondition and not invar.precondition(self):
                continue
            await invar.function(self)


# Monkey patching

def monkey_patch_hypothesis():
    from hypothesis import stateful
    stateful._old_run_state_machine_as_test = stateful.run_state_machine_as_test
    stateful.run_state_machine_as_test = run_state_machine_as_test


monkey_patch_hypothesis()

# Expose all objects from original stateful module
from hypothesis.stateful import *
