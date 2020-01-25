Release history
===============

.. currentmodule:: hypothesis_trio

.. towncrier release notes start

Hypothesis_Trio 0.5.0 (2020-01-11)
----------------------------------

Update to hypothesis version 5 (more precisely, ``hypothesis>=5.1.4``).

Hypothesis_Trio 0.4.0 (2019-06-26)
----------------------------------

Add ``TrioAsyncioGenericStateMachine`` to support trio-asyncio.

Hypothesis_Trio 0.3.1 (2019-02-13)
----------------------------------

This patch fixes hypothesis-trio's license compliance, by changing the
license to the Mozilla Public License 2.0.  This is required because
hypothesis-trio is substantively a modified version of the ``stateful``
module from Hypothesis, under file-based copyleft, and has the agreement
of all contributors to hypothesis-trio.

Hypothesis_Trio 0.3.0 (2019-02-11)
----------------------------------

Fix support of Hypothesis 4.0.
Switch to trio>=0.11 as dependency requirement.

Hypothesis_Trio 0.2.2 (2018-08-29)
----------------------------------

Fix behovior of ``TrioGenericStateMachine.set_clock`` and ``TrioGenericStateMachine.push_instrument``.

Hypothesis_Trio 0.2.1 (2018-07-17)
----------------------------------

Fix crash during final error print.


Hypothesis_Trio 0.2.0 (2018-07-16)
----------------------------------

Rename ``TrioRuleBasedAsyncStateMachine`` -> ``TrioRuleBasedStateMachine``.


Hypothesis_Trio 0.1.0 (2018-07-16)
----------------------------------

Initial commit.
