Tips
====

To run tests
------------

* Install requirements: ``pip install -r test-requirements.txt``
  (possibly in a virtualenv)

* Actually run the tests: ``pytest hypothesis_trio``


To run yapf
-----------

* Show what changes yapf wants to make: ``yapf -rpd setup.py
  hypothesis_trio``

* Apply all changes directly to the source tree: ``yapf -rpi setup.py
  hypothesis_trio``


To make a release
-----------------

* Update the version in ``hypothesis_trio/_version.py``

* Run ``towncrier`` to collect your release notes.

* Review your release notes.

* Check everything in.

* Double-check it all works, docs build, etc.

* Build your sdist and wheel: ``python setup.py sdist bdist_wheel``

* Upload to PyPI: ``twine upload dist/*``

* Use ``git tag`` to tag your version.

* Don't forget to ``git push --tags``.
