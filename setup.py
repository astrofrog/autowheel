from setuptools import setup, find_packages

entry_points = """
[console_scripts]
autowheel = autowheel.autowheel:main
"""

setup(name='autowheel',
      version='0.1.dev0',
      description='Automatically build wheels from PyPI releases',
      long_description=open('README.rst').read(),
      install_requires=['click', 'cibuildwheel', 'requests', 'pyyaml'],
      author='Thomas Robitaille',
      author_email='thomas.robitaille@gmail.com',
      license='BSD',
      url='https://github.com/astrofrog/autowheel',
      entry_points=entry_points,
      packages=find_packages())
