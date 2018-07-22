#!/usr/bin/env python
import os
import sys

from setuptools import find_packages, setup

wrench_root_dir = os.path.abspath(os.path.dirname(__file__))
src_root_dir = os.path.join(wrench_root_dir, 'src')
sys.path.append(src_root_dir)

tests_require = [
    'pytest',
    'pytest-cov',
    'factory-boy',
]

install_requires = [
    'click>=6.0',
    'requests',
    'requests_gpgauthlib>=0.1.0',
]

version = __import__('wrench').__version__

setup(
    name='passbolt-wrench',
    version=version,
    package_dir={"": 'src'},
    packages=find_packages(
        where=src_root_dir
    ),
    description='wrench is a CLI for Passbolt',
    author='The wrench developers',
    author_email='wrench@liip.ch',
    url='https://github.com/liip/wrench',
    install_requires=install_requires,
    setup_requires=['pytest-runner'],
    license='GPLv3+',
    tests_require=tests_require,
    include_package_data=False,
    entry_points={
        'console_scripts': 'wrench = wrench.commands:main'
    },
    classifiers=[
        'Environment :: Console',
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
