PYTHON_TAGS = ['cp27', 'cp34', 'cp35', 'cp36', 'cp37', 'cp38', 'cp39']

# The platform tags use syntax compatible with fnmatch since that is what is
# used by cibuildwheel, and also when we check existing builds on PyPI.
PLATFORM_TAGS = {'macosx': 'macosx_10_?_*',
                 'linux32': 'manylinux*_i686',
                 'linux64': 'manylinux*_x86_64',
                 'windows32': 'win32',
                 'windows64': 'win_amd64'}
