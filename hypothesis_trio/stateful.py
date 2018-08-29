import trio
from trio.testing import trio_test
import hypothesis.internal.conjecture.utils as cu
from hypothesis._settings import Verbosity
from hypothesis.reporting import current_verbosity
from hypothesis.stateful import (
    VarReference,
    GenericStateMachine,
    StateMachineRunner,
    run_state_machine_as_test,
    Bundle,
    rule,
    initialize,
    precondition,
    invariant,
    RuleBasedStateMachine,
)


def monkey_patch_hypothesis():
    def run(self, state_machine, print_steps=None):
        if print_steps is None:
            print_steps = current_verbosity() >= Verbosity.debug
        self.data.hypothesis_runner = state_machine

        should_continue = cu.many(
            self.data,
            min_size=1,
            max_size=self.n_steps,
            average_size=self.n_steps,
        )

        def _default_runner(data, print_steps, should_continue):
            try:
                if print_steps:
                    state_machine.print_start()
                state_machine.check_invariants()

                while should_continue.more():
                    value = data.draw(state_machine.steps())
                    if print_steps:
                        state_machine.print_step(value)
                    state_machine.execute_step(value)
                    state_machine.check_invariants()
            finally:
                if print_steps:
                    state_machine.print_end()
                state_machine.teardown()

        runner = getattr(state_machine, '_custom_runner', _default_runner)
        runner(self.data, print_steps, should_continue)

    StateMachineRunner.run = run


monkey_patch_hypothesis()


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
                        value = data.draw(self.steps())
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
            name = self.new_name()
            self.names_to_values[name] = result
            # TODO: not really elegant to access __printer this way...
            self._RuleBasedStateMachine__printer.singleton_pprinters.setdefault(
                id(result), lambda obj, p, cycle: p.text(name)
            )
            for target in rule.targets:
                self.bundle(target).append(VarReference(name))
        if self._initialize_rules_to_run:
            self._initialize_rules_to_run.remove(rule)

    async def check_invariants(self):
        for invar in self.invariants():
            if invar.precondition and not invar.precondition(self):
                continue
            await invar.function(self)


__all__ = (
    'VarReference',
    'GenericStateMachine',
    'StateMachineRunner',
    'run_state_machine_as_test',
    'Bundle',
    'rule',
    'initialize',
    'precondition',
    'invariant',
    'RuleBasedStateMachine',
    'TrioGenericStateMachine',
    'TrioRuleBasedStateMachine',
)
