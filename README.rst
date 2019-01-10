|Travis| |AppVeyor|

About
-----

This package is a wrapper around the
`cibuildwheel <https://github.com/joerick/cibuildwheel>`__ tool, and makes it
easy to automate building wheels from PyPI source releases rather than
for a source repository.

Note that this is intended to be used with packages that require
platform-specific wheels. If you have a pure-Python package, you can probably
just build a universal wheel with::

    python setup.py bdist_wheel --universal

Basic usage
-----------

To use autowheel, you should first follow the instructions for setting up
`cibuildwheel <https://github.com/joerick/cibuildwheel>`__, but instead of
running::

    pip install cibuildwheel==0.9.4
    cibuildwheel --output-dir wheelhouse

You should instead run::

    pip install autowheel
    autowheel platform --output-dir wheelhouse

where platform is one of ``macos``, ``linux``, or ``windows``. In addition,
you should create a file ``autowheel.yml`` that contains a file that looks like::

    - package_name: mpl-scatter-density
      python_versions:
        '0.1':
          - cp27
          - cp34
          - cp35
          - cp36
          - cp37
        '0.2':
          - cp34
          - cp35
          - cp36
          - cp37

The meaning of ``python_version`` is the Python versions that should be build
for each package version - but note that you don't need to specify all the
package versions - just the ones where the required Python versions change. If
the version is not one of the ones listed, the latest one that is equal or less
than the required one will be used - in the above example, version 0.1.1 would
be built with the same Python versions as 0.1, and 0.3 would be built with the
same versions as 0.2.

The way autowheel works is that it will look at all the releases of the package
on PyPI that are more recent than the oldest version mentioned in the
``autowheel.yml`` file, and for each of them it will determine whether any
wheels are missing. If so, then wheel are built for all Python versions
specified, and placed in the output directory. To force all wheels to be built
even if they already exist, use the ``--build-existing`` option::

    autowheel platform --output-dir wheelhouse --build-existing

Note that you can list multiple packages inside a single ``autowheel.yml`` file,
and you can also list the same package multiple times with different
configuration if needed.

Options
-------

There are a few options that you can add to the configuration to customize the
build process, and which we now describe.

before_build
^^^^^^^^^^^^

You can also specify a ``before_build`` key with a command that should be run
before the wheel is built, e.g.::

    - package_name: fast-histogram
      before_build: pip install numpy==1.12.1
      python_versions:
        '0.1':
          - cp27

Note that if you want to pin Numpy, you should take a look at the ``pin_numpy``
option instead.

pin_numpy and pin_numpy_min
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Wheels that require Numpy as a build-time dependency are typically built against
the oldest compatible version of Numpy on each platform and for each Python
version. Rather than having to figure this out manually, you can simply set
the ``pin_numpy`` option as follows::

    - package_name: fast-histogram
      pin_numpy: true
      python_versions:
        '0.1':
          - cp27
          - cp35

and autowheel will automatically determine the correct Numpy version to pin
against (it does this by determining the version of the oldest available numpy
wheels for each platform and python version).

In some cases, this might pick a version of Numpy that is too old for the
package you are building, so you can specify an absolute minimum version with
the ``pin_numpy_min`` option::

    - package_name: fast-histogram
      pin_numpy: true
      pin_numpy_min: 1.13.0
      python_versions:
        '0.1':
          - cp27
          - cp35

This means that autowheel will pin Numpy to the oldest compatible version or
1.13.0, whichever is more recent.

test_command and test_requires
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An important step when building wheels is to make sure that the built package
works properly. You can specify a test command to run after the build using the
``test_command`` option::

    - package_name: fast-histogram
      test_command: pytest --pyargs fast_histogram
      python_versions:
        '0.1':
          - cp27
          - cp35

In the above case, the ``--pyargs`` ensures that we test the installed version
of the package rather than the source directory. Note that currently due to the
way cibuildwheel works, the tests are run in the same environment as the build
environment, so any build-time dependencies installed will still be available
(this may change in future).

To install additional dependencies into the test environment (e.g. pytest)
or to update dependencies that were installed during the build process, you can
use the ``test_requires`` option::

  - package_name: fast-histogram
    test_command: pytest --pyargs fast_histogram
    test_requires: pytest numpy==1.15.4
    python_versions:
      '0.1':
        - cp27
        - cp35

.. |Travis| image:: https://travis-ci.org/astrofrog/autowheel.svg?branch=master
    :target: https://travis-ci.org/astrofrog/autowheel

.. |AppVeyor| image:: https://ci.appveyor.com/api/projects/status/9n8kr8gnvlrj3lqi/branch/master?svg=true
    :target: https://ci.appveyor.com/project/astrofrog/autowheel
