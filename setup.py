#!/usr/bin/env python
from setuptools import find_packages, setup

tests_require = [
]

install_requires = [
    'click>=6.0',
    'requests',
    'requests_gpgauthlib',
]


setup(
    name='passbolt-wrench',
    version='0.0.1',
    package_dir={"": "src"},
    packages=find_packages(
        where='src'
    ),
    description='wrench is a CLI for Passbolt',
    author='The wrench developers',
    author_email='wrench@liip.ch',
    url='https://github.com/liip/wrench',
    install_requires=install_requires,
    license='GPLv3+',
    tests_require=tests_require,
    include_package_data=False,
    entry_points={
        'console_scripts': 'wrench = wrench.commands:main'
    },
    classifiers=[
        'Environment :: Console',
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
