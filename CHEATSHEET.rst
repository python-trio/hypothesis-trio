Tips
====

To run tests
------------

* Install requirements: ``pip install -r test-requirements.txt``
  (possibly in a virtualenv)

* Actually run the tests: ``pytest hypothesis_trio``


To run Q&A
----------

* To check&correct coding style: ``black hypothesis_trio setup.py``
* To lint code: ``flake8 hypothesis_trio setup.py``


To make a release
-----------------

* Update the version in ``hypothesis_trio/_version.py``

* Run ``towncrier`` to collect your release notes.

* Review your release notes.

* Check everything in.

* Double-check it all works, docs build, etc.

* Install build (wheel builder) and twine (wheel uploader): ``pip install build twine``

* Make sure you dist folder is clean: ``rm -rf ./dist``

* Build your sdist and wheel: ``python -m build``

* Upload to PyPI: ``twine upload dist/*``

* Use ``git tag`` to tag your version.

* Don't forget to ``git push --tags``.
