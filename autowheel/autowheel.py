from __future__ import print_function

import os
import sys

import click
import tarfile
import tempfile
from fnmatch import fnmatch
from distutils.version import LooseVersion

import requests
from yaml import load

from cibuildwheel.__main__ import main as cibuildwheel

from .numpy import MIN_NUMPY
from .config import PYTHON_TAGS, PLATFORM_TAGS


def process(platform_tag=None, before_build=None, package_name=None,
            python_versions=None, output_dir=None, build_existing=False,
            test_command=None, test_requires=None, pin_numpy=False, pin_numpy_min=None):

    print('Processing {package_name}'.format(package_name=package_name))

    # The keys of the python_versions dictionary are versions of the package.
    # For example, the dictionary might be:
    #
    #    {'0.1': ['cp27', 'cp35'], '0.2': ['cp27', 'cp35', 'cp36']}
    #
    # which means that package versions in the range [0.1:0.2) will be built for
    # Python 2.7 and 3.5, and versions greater or equal to 0.2 will also be
    # built for Python 3.6. Versions before 0.1 won't be built.

    # Start off by finding all specified package versions (as mentioned above,
    # these are just the versions where the required Python versions change, but
    # all versions in between and more recent will be checked/built too)
    package_versions = [LooseVersion(package_version) for package_version in python_versions]
    min_package_version = min(package_versions)

    # Prepare PyPI URL
    pypi_data = requests.get('https://pypi.org/pypi/{package_name}/json'.format(package_name=package_name)).json()

    # Remember where we started - if anything goes wrong we'll go back there
    # at the end.
    start_dir = os.path.abspath('.')

    # Loop over all releases on PyPI, and check what wheels should be built for
    # each release. Wheels that already exist on PyPI won't be built since they
    # can't be replaced.
    for release_version in sorted(pypi_data['releases']):

        if 'rc' in release_version:
            continue

        print('Release: {release_version}... '.format(release_version=release_version), end='')

        # Any package version older than the oldest specified one shouldn't be built
        if LooseVersion(release_version) < min_package_version:
            print('skipping')
            continue

        # Find the package version in the config that is equal to or is the most
        # recent one before the target release.
        matching_version = max([package_version
                                for package_version in package_versions
                                if package_version <= LooseVersion(release_version)])

        # Figure out which Python versions are requested in the config
        required_pythons = python_versions[str(matching_version)]

        # Now determine which Python versions have already been built for the
        # target OS and are on PyPI. Note that for a given platform there are
        # multiple possible tags. If *any* of the platform tags match, we
        # consider the wheel already built.

        files = pypi_data['releases'][release_version]

        wheels_pythons = []
        sdist = None
        for fileinfo in files:
            if fileinfo['packagetype'] == 'bdist_wheel':
                filename = fileinfo['filename']
                if fnmatch(filename, '*{0}*'.format(platform_tag)):
                    for python_tag in PYTHON_TAGS:
                        if python_tag in filename:
                            wheels_pythons.append(python_tag)
            elif fileinfo['packagetype'] == 'sdist':
                sdist = fileinfo

        if build_existing:
            missing = sorted(set(required_pythons))
        else:
            missing = sorted(set(required_pythons) - set(wheels_pythons))
            if not missing:
                print('all wheels present')
                continue

        print('missing wheels:', missing)

        # We now build the missing wheels

        try:

            tmpdir = tempfile.mkdtemp()
            print('Changing to {0}'.format(tmpdir))
            os.chdir(tmpdir)

            print('  Fetching {url}'.format(**sdist))
            req = requests.get(sdist['url'])
            with open(sdist['filename'], 'wb') as f:
                f.write(req.content)

            print('  Expanding {filename}'.format(**sdist))
            tar = tarfile.open(sdist['filename'], 'r:gz')
            tar.extractall(path='.')

            # Find directory name
            paths = os.listdir('.')
            paths.remove(sdist['filename'])
            if len(paths) > 1:
                raise ValueError('Unexpected files/directories:', paths)
            print('  Go into directory {0}'.format(paths[0]))
            os.chdir(paths[0])

            # We now configure cibuildwheel via environment variables

            print('  Running cibuildwheel')

            sys.argv = ['cibuildwheel', '.']

            if 'mac' in platform_tag:
                os.environ['CIBW_PLATFORM'] = 'macos'
            elif 'linux' in platform_tag:
                os.environ['CIBW_PLATFORM'] = 'linux'
            else:
                os.environ['CIBW_PLATFORM'] = 'windows'

            os.environ['CIBW_OUTPUT_DIR'] = str(output_dir)
            if test_command:
                os.environ['CIBW_TEST_COMMAND'] = str(test_command)
            if test_requires:
                os.environ['CIBW_TEST_REQUIRES'] = str(test_requires)

            os.environ['CIBW_BUILD_VERBOSITY'] = '3'

            for python_tag in missing:

                os.environ['CIBW_BUILD'] = "{0}-{1}".format(python_tag, platform_tag)

                if pin_numpy:
                    pinned_version = MIN_NUMPY[python_tag][platform_tag]
                    if pin_numpy_min is not None and LooseVersion(pinned_version) < pin_numpy_min:
                        pinned_version = pin_numpy_min
                    os.environ['CIBW_BEFORE_BUILD'] = 'pip install numpy=={0}'.format(pinned_version)
                elif before_build:
                    os.environ['CIBW_BEFORE_BUILD'] = str(before_build)

                for key, value in os.environ.items():
                    if key.startswith('CIBW'):
                        print('{0}: {1}'.format(key, value))

                try:
                    cibuildwheel()
                except SystemExit as exc:
                    if exc.code != 0:
                        raise

        finally:

            os.chdir(start_dir)


@click.command()
@click.argument('platform', type=click.Choice(['macosx', 'windows32', 'windows64', 'linux32', 'linux64']))
@click.option('--output-dir', type=click.Path(exists=True), default='.')
@click.option('--package', type=str, default=None)
@click.option('--build-existing/--no-build-existing', default=False)
def main(platform, output_dir, package, build_existing):

    target_package_name = package

    output_dir = os.path.abspath(output_dir)

    with open('autowheel.yml') as f:
        packages = load(f)

    for package in packages:

        if target_package_name is not None and target_package_name != package['package_name']:
            continue

        process(platform_tag=PLATFORM_TAGS[platform],
                before_build=package.get('before_build'),
                pin_numpy=package.get('pin_numpy', False),
                pin_numpy_min=package.get('pin_numpy_min'),
                package_name=package['package_name'],
                python_versions=package['python_versions'],
                test_command=package['test_command'],
                test_requires=package['test_requires'],
                output_dir=output_dir,
                build_existing=build_existing)
