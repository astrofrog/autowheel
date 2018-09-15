About
-----

This package is a wrapper around the
`cibuildwheel <https://github.com/joerick/cibuildwheel>`_ tool, and makes it
easy to automate building wheels from PyPI source releases rather than
for a source repository.

To use this, you should first follow the instructions for setting up
`cibuildwheel <https://github.com/joerick/cibuildwheel>`_, but instead of
running::

    $PIP install cibuildwheel==0.9.4
    cibuildwheel --output-dir wheelhouse

You should instead run::

    $PIP install autowheel
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
