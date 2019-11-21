# This module keeps track of the oldest versions of Numpy that can be built
# against - based on what versions wheels are available for.
from distutils.version import LooseVersion
from collections import defaultdict
from fnmatch import fnmatch

import requests

from .config import PYTHON_TAGS, PLATFORM_TAGS

__all__ = ['MIN_NUMPY']

MIN_NUMPY = defaultdict(dict)

pypi_data = requests.get('https://pypi.org/pypi/numpy/json').json()

# Get rid of pre-releases and versions before 1.9.x
versions = []
for version in pypi_data['releases']:
    try:
        [int(x) for x in version.split('.')]
    except ValueError:
        continue
    else:
        if LooseVersion(version) >= '1.9':
            versions.append(version)

for version in sorted(versions, key=lambda x: LooseVersion(x)):

    files = pypi_data['releases'][version]

    for fileinfo in files:
        if fileinfo['packagetype'] == 'bdist_wheel':
            filename = fileinfo['filename']

            for python_tag in PYTHON_TAGS:
                if python_tag in filename:
                    for platform_tag in PLATFORM_TAGS.values():
                        if fnmatch(filename, '*{0}*'.format(platform_tag)):
                            if (platform_tag not in MIN_NUMPY[python_tag] or
                                    MIN_NUMPY[python_tag][platform_tag].split('.')[:2] == version.split('.')[:2]):
                                MIN_NUMPY[python_tag][platform_tag] = version
