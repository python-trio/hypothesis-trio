from setuptools import setup, find_packages

# Awesome hack to load `__version__`
__version__ = None
exec(open("hypothesis_trio/_version.py", encoding="utf-8").read())

LONG_DESC = open("README.rst", encoding="utf-8").read()

setup(
    name="hypothesis-trio",
    version=__version__,
    description="Hypothesis plugin for trio",
    url="https://github.com/python-trio/hypothesis-trio",
    long_description=open("README.rst").read(),
    author="Emmanuel Leblond",
    author_email="emmanuel.leblond@gmail.com",
    license="MPL 2.0",
    packages=find_packages(),
    # Note: There is no use setting a upper bound for hypothesis given we rely
    # on internals that are subject to change even between minor versions !
    install_requires=["trio>=0.11", "hypothesis>=6.7.0"],
    keywords=[
        "async",
        "hypothesis",
        "testing",
        "trio",
    ],
    python_requires=">=3.6",
    classifiers=[
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: System :: Networking",
        "Topic :: Software Development :: Testing",
        "Framework :: Hypothesis",
        "Framework :: Trio",
    ],
)
