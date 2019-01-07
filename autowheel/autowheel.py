from __future__ import print_function

import os
import sys

import click
import tarfile
import tempfile
import requests
from yaml import load
from distutils.version import LooseVersion
from collections import defaultdict

from cibuildwheel.__main__ import main as cibuildwheel


def process(target_platform=None, before_build=None, package_name=None, python_versions=None, output_dir=None, ignore_existing=False):

    print('Processing {package_name}'.format(package_name=package_name))

    # The keys of the python_versions dictionary are versions of the package.
    # For example, the dictionary might be:
    #
    #    {'0.1': ['cp27', 'cp35'], '0.2': ['cp27', 'cp35', 'cp36']}
    #
    # which means that package versions in the range [0.1:0.2) will be built for
    # Python 2.7 and 3.5, and versions greater or equal to 0.2 will also be
    # built for Python 3.6. Versions before 0.1 won't be built.
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
    for release_version in pypi_data['releases']:

        print('Release: {release_version}... '.format(release_version=release_version), end='')

        if LooseVersion(release_version) < min_package_version:
            print('skipping')
            continue

        # Find the package version in the config that is equal to or is the most
        # recent one before the target release.
        matching_version = max([package_version for package_version in package_versions if package_version <= LooseVersion(release_version)])

        # Figure out which Python versions are requested in the config
        required_pythons = python_versions[str(matching_version)]

        # Now determine which Python versions have already been built for the
        # target OS.

        files = pypi_data['releases'][release_version]

        wheels = defaultdict(list)

        sdist = None

        for fileinfo in files:
            if fileinfo['packagetype'] == 'bdist_wheel':
                filename = fileinfo['filename']
                python_version = filename.split('-')[2]
                if 'macosx' in filename:
                    platform = 'macos'
                elif 'manylinux1_x86_64' in filename:
                    platform = 'linux32'
                elif 'manylinux1_i686' in filename:
                    platform = 'linux64'
                elif 'win32' in filename:
                    platform = 'windows32'
                elif 'win_amd64' in filename:
                    platform = 'windows64'
                else:
                    continue
                wheels[platform].append(python_version)
            elif fileinfo['packagetype'] == 'sdist':
                sdist = fileinfo

        wheels['windows'] = set(wheels['windows32']) & set(wheels['windows64'])
        wheels['linux'] = set(wheels['linux32']) & set(wheels['linux64'])

        missing = sorted(set(required_pythons) - set(wheels[target_platform]))

        if not missing and not ignore_existing:
            print('all wheels present')
            continue

        print('missing wheels:', missing)

        tmpdir = tempfile.mkdtemp()
        try:

            print('Changing to {0}'.format(tmpdir))
            os.chdir(tmpdir)

            print('  Fetching {0}'.format(sdist["url"]))
            req = requests.get(sdist['url'])
            with open(sdist['filename'], 'wb') as f:
                f.write(req.content)

            print('  Expanding {0}'.format(sdist["filename"]))
            tar = tarfile.open(sdist['filename'], 'r:gz')
            tar.extractall(path='.')

            # Find directory name
            paths = os.listdir('.')
            paths.remove(sdist['filename'])
            if len(paths) > 1:
                raise ValueError('Unexpected files/directories:', paths)
            print('  Go into directory {0}'.format(paths[0]))
            os.chdir(paths[0])

            print('  Running cibuildwheel')

            sys.argv = ['cibuildwheel', '.']
            os.environ['CIBW_BUILD'] = ' '.join([pyver + '-*' for pyver in missing])
            os.environ['CIBW_PLATFORM'] = str(target_platform)
            os.environ['CIBW_OUTPUT_DIR'] = str(output_dir)
            if before_build:
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
@click.argument('platform', type=click.Choice(['macos', 'windows', 'linux', 'osx']))
@click.option('--output-dir', type=click.Path(exists=True), default='.')
@click.option('--ignore-existing/--no-ignore-existing', default=False)
def main(platform, output_dir, ignore_existing):

    if platform == 'osx':
        platform = 'macos'

    output_dir = os.path.abspath(output_dir)

    with open('autowheel.yml') as f:
        packages = load(f)

    for package in packages:
        process(target_platform=platform,
                before_build=package.get('before_build', None),
                package_name=package['package_name'],
                python_versions=package['python_versions'],
                output_dir=output_dir,
                ignore_existing=ignore_existing)
