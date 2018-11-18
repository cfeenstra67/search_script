#!/usr/bin/env python

from distutils.core import setup

setup(
	name='search',
	version='1.0',
	description='Simple script for searching files & filenames',
	author='Cam Feenstra',
	author_email='cameron.l.feenstra@gmail.com',
	packages=['search'],
	entry_points={
		'console_scripts': [
			'search = search.__main__:main'
		]
	},
	extras_require={
		'yaml': 'PyYAML'
	}
)