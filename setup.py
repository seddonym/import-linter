#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import io
from glob import glob
from os.path import basename, dirname, join, splitext

from setuptools import find_packages, setup


def read(*names, **kwargs):
    with io.open(
        join(dirname(__file__), *names), encoding=kwargs.get("encoding", "utf8")
    ) as fh:
        return fh.read()


setup(
    name="import-linter",
    version="1.2.2",
    license="BSD 2-Clause License",
    description="Enforces rules for the imports within and between Python packages.",
    long_description=read("README.rst"),
    long_description_content_type="text/x-rst",
    author="David Seddon",
    author_email="david@seddonym.me",
    project_urls={
        "Documentation": "https://import-linter.readthedocs.io/",
        "Source code": "https://github.com/seddonym/import-linter/",
    },
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Utilities",
    ],
    python_requires=">=3.6",
    install_requires=["click>=6,<9", "grimp>=1.2.3,<2"],
    entry_points={
        "console_scripts": ["lint-imports = importlinter.cli:lint_imports_command"]
    },
)
