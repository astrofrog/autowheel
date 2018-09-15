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



def process(target_platform=None, package_name=None, python_versions=None, wheelhouse_dir=None):

    print('Processing {package_name}'.format(package_name=package_name))

    versions = [LooseVersion(version) for version in python_versions]

    min_version = min(versions)

    pypi_data = requests.get('https://pypi.org/pypi/{package_name}/json'.format(package_name=package_name)).json()

    start_dir = os.path.abspath('.')

    for release in pypi_data['releases']:

        print('Release: {release}... '.format(release=release), end='')

        if LooseVersion(release) < min_version:
            print('skipping')
            continue

        release_version = release.split('rc')[0]
        matching_version = max([version for version in versions if version <= LooseVersion(release_version)])

        required_pythons = python_versions[str(matching_version)]

        files = pypi_data['releases'][release]

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
                    raise ValueError("Could not determine platform:", filename)
                wheels[platform].append(python_version)
            elif fileinfo['packagetype'] == 'sdist':
                sdist = fileinfo

        wheels['windows'] = set(wheels['windows32']) & set(wheels['windows64'])
        wheels['linux'] = set(wheels['linux32']) & set(wheels['linux64'])

        missing = sorted(set(required_pythons) - set(wheels[target_platform]))

        if not missing:
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
            os.environ['CIBW_PLATFORM'] = target_platform
            os.environ['CIBW_OUTPUT_DIR'] = wheelhouse_dir

            cibuildwheel()

        finally:

            os.chdir(start_dir)


@click.command()
@click.argument('platform', type=click.Choice(['macos', 'windows', 'linux', 'osx']))
@click.option('--output-dir', type=click.Path(exists=True), default='.')
def main(platform, wheelhouse_dir):

    if platform == 'osx':
        platform = 'macos'

    wheelhouse_dir = os.path.abspath(wheelhouse_dir)

    with open('autowheel.yml') as f:
        packages = load(f)

    for package in packages:
        process(target_platform=platform,
                package_name=package['package_name'],
                python_versions=package['python_versions'],
                wheelhouse_dir=wheelhouse_dir)
