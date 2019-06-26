===============
hypothesis-trio
===============

.. image:: https://travis-ci.org/python-trio/hypothesis-trio.svg?branch=master
    :target: https://travis-ci.org/python-trio/hypothesis-trio

.. image:: https://codecov.io/gh/python-trio/hypothesis-trio/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/python-trio/hypothesis-trio

Welcome to `hypothesis-trio <https://github.com/python-trio/hypothesis-trio>`__!

Hypothesis supports Trio out of the box for non-stateful tests.
This project aims at supporting the stateful mode ;-)

License: Your choice of MIT or Apache License 2.0


Usage
=====

Replace ``hypothesis.stateful.RuleBasedStateMachine`` by ``hypothesis_trio.stateful.TrioRuleBasedStateMachine``:

.. code-block:: python

    from hypothesis_trio.stateful import TrioRuleBasedStateMachine, run_state_machine_as_test


    def test_trio_number_modifier(hypothesis_settings):
        class NumberModifier(TrioRuleBasedStateMachine):

            folders = Bundle('folders')
            files = Bundle('files')

            @initialize(target=folders)
            async def init_folders(self):
                await trio.sleep(0)
                return '/'

            @rule(target=folders, name=name_strategy)
            async def create_folder(self, parent, name):
                await trio.sleep(0)
                return '%s/%s' % (parent, name)

            @rule(target=files, name=name_strategy)
            async def create_file(self, parent, name):
                await trio.sleep(0)
                return '%s/%s' % (parent, name)

            async def teardown(self):
                await trio.sleep(0)

        run_state_machine_as_test(NumberModifier, settings=hypothesis_settings)


Support for Trio-Asyncio
=========================


`trio-asyncio <https://github.com/python-trio/trio-asyncio>`__ allows to mix asyncio and trio code altogether.
To support it in your test, you should use ``hypothesis_trio.stateful.TrioAsyncioRuleBasedStateMachine``:

.. code-block:: python

    class CheckAsyncioLoop(TrioAsyncioRuleBasedStateMachine):

        @initialize()
        async def initialize(self):
            assert self.get_asyncio_loop() == asyncio.get_event_loop()
            await trio_asyncio.aio_as_trio(lambda: asyncio.sleep(0))
