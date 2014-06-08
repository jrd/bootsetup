#!/bin/env python
# coding: utf-8
# vim:et:sta:sw=2:sts=2:ts=2:tw=0:

import os
import codecs
import re
from setuptools import setup


def read(*paths):
  """Build a file path from *paths* and return the contents."""
  with codecs.EncodedFile(open(os.path.join(*paths), 'rb'), 'utf-8') as f:
    return f.read()


def find_info(info, *file_paths):
  info_file = read(*file_paths)
  info_match = re.search(r"^__{0}__ = ['\"]([^'\"]*)['\"]".format(info), info_file, re.M)
  if info_match:
    return info_match.group(1)
  raise RuntimeError("Unable to find {0} string.".format(info))


def find_version(*file_paths):
  return find_info('version', *file_paths)


config = {
  'name': 'BootSetup',
  'description': 'Helps installing a bootloader like LiLo or Grub2 on your computer',
  'long_description': read('README.rst'),
  'license': find_info('license', 'bootsetup', 'bootsetup.py'),
  'author': find_info('author', 'bootsetup', 'bootsetup.py'),
  'author_email': find_info('email', 'bootsetup', 'bootsetup.py'),
  'version': find_version('bootsetup', 'bootsetup.py'),
  'url': 'https://github.com/jrd/bootsetup/',
  'download_url': 'https://github.com/jrd/bootsetup/archive/master.zip',
  'packages': ['bootsetup'],
  'include_package_data': True,
  'package_data': {'bootsetup': ['*.glade']},
  'entry_points': {'console_scripts': ['bootsetup = bootsetup.bootsetup:main']},
  'classifiers': [  # https://pypi.python.org/pypi?:action=list_classifiers
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Environment :: Console :: Curses',
    'Environment :: X11 Applications',
    'Environment :: X11 Applications :: GTK',
    'Intended Audience :: End Users/Desktop',
    'Intended Audience :: System Administrators',
    'Natural Language :: English',
    'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.3',
    'Topic :: System :: Boot',
    'Topic :: System :: Recovery Tools',
  ],
}
setup(**config)
