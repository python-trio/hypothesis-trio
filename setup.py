from setuptools import setup, find_packages

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
    license="MIT -or- Apache License 2.0",
    packages=find_packages(),
    install_requires=[
        "trio",
    ],
    keywords=[
        'async',
        'hypothesis',
        'testing',
        'trio',
    ],
    python_requires=">=3.5",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: System :: Networking",
        "Topic :: Software Development :: Testing",
        "Framework :: Trio",
    ],
)
