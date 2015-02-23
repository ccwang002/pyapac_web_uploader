from pathlib import Path
import re
from setuptools import setup, find_packages


def find_version(*path_parts):
    with Path(*path_parts).open(encoding='utf8') as f:
        version_match = re.search(
            r"^__version__ = ['\"]([^'\"]*)['\"]",
            f.read(), re.M
        )
    if version_match:
        return version_match.group(1)

    raise RuntimeError("Unable to find version string.")


setup(
    name='pyapac-webtool',
    version=find_version('pyapacweb.py'),

    license='MIT',
    description='Web content tools for PyCon APAC 2015',

    author='PyCon APAC 2015 organizers',
    author_email='organizers@pycon.tw',

    url='https://github.com/ccwang002/pyapac_web_uploader',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords=['pycon', 'apac', '2015', 'taiwan'],

    install_requires=['requests > 2.5', 'beautifulsoup4 > 4.3', 'click'],

    packages=find_packages(
        exclude=[
            'contrib', 'docs', 'examples', 'deps',
            '*.tests', '*.tests.*', 'tests.*', 'tests',
        ]
    ),
    py_modules=['pyapacweb'],

    test_suite='nose.collector',
    entry_points={
        'console_scripts': [
            'pyapac-web = pyapacweb:cli',
        ]
    },
)
