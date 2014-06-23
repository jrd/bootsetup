#!/bin/env python
# coding: utf-8
# vim:et:sta:sw=2:sts=2:ts=2:tw=0:
from __future__ import division, print_function, absolute_import

from setuptools import setup
from distutils import cmd
from distutils.command.build import build as build_class
from distutils.command.install import install as install_class
from distutils.command.install_data import install_data as install_data_class
import os
import codecs
import re
from glob import glob
import polib
import subprocess as sp
import shutil


MODULE_NAME = 'bootsetup'


def read(*paths):
  """Build a file path from *paths* and return the contents."""
  with codecs.EncodedFile(open(os.path.join(*paths), 'rb'), 'utf-8') as f:
    return f.read()


def find_info(info, *file_paths):
  file_paths = list(file_paths)
  file_paths.append('__init__.py')
  info_file = read(*file_paths)
  python_simple_string = r"(?:[^'\"\\]*)"
  python_escapes = r"(?:\\['\"\\])"
  python_string = r"{delim}((?:{simple}{esc}?)*){delim}".format(delim=r"['\"]", simple=python_simple_string, esc=python_escapes)
  info_match = re.search(r"^__{0}__ = {1}".format(info, python_string), info_file, re.M)
  if info_match:
    return info_match.group(1)
  else:
    python_arrays = r"\[(?:{ps})?((?:, {ps})*)\]".format(ps=python_string)
    info_match = re.search(r"^__{0}__ = {1}".format(info, python_arrays), info_file, re.M)
    if info_match:
      matches = [info_match.group(1)]
      if info_match.groups(2):
        matches.extend(re.findall(r", {0}".format(python_string), info_match.group(2)))
      return ', '.join(matches)
  raise RuntimeError("Unable to find {0} string.".format(info))


def find_version(*file_paths):
  return find_info('version', *file_paths)


class build_trans(cmd.Command):
  """
  Compile .po files to .mo files and .desktop.in to .desktop
  """
  description = __doc__

  def initialize_options(self):
    pass

  def finalize_options(self):
    pass

  def run(self):
    po_dir = os.path.join('resources', 'po')
    for pot_name in [os.path.basename(filename)[:-4] for filename in glob(os.path.join(po_dir, '*.pot'))]:
      print('* Compiling po files for {0}'.format(pot_name))
      for po_file in glob(os.path.join(po_dir, '*.po')):
        lang = os.path.basename(po_file)[:-3]  # len('.po') == 3
        mo_file = os.path.join('build', 'locale', lang, 'LC_MESSAGES', '{0}.mo'.format(pot_name))
        mo_dir = os.path.dirname(mo_file)
        if not os.path.exists(mo_dir):
          os.makedirs(mo_dir)
        create_mo = False
        if not os.path.exists(mo_file):
          create_mo = True
        else:
          po_mtime = os.stat(po_file)[8]
          mo_mtime = os.stat(mo_file)[8]
          if po_mtime > mo_mtime:
            create_mo = True
        if create_mo:
          print('** Compiling {0}'.format(po_file))
          po = polib.pofile(po_file)
          po.save_as_mofile(mo_file)
    for in_file in glob(os.path.join('resources', '*.desktop.in')):
      out_file = os.path.join('build', os.path.basename(in_file)[:-3])  # len('.in') == 3
      sp.check_call(['intltool-merge', po_dir, '-d', '-u', in_file, out_file])


class build_icons(cmd.Command):
  """
  Copy icons files to the build directory.
  """
  description = __doc__

  def initialize_options(self):
    pass

  def finalize_options(self):
    pass

  def run(self):
    icons_dir = os.path.join('resources', 'icons')
    for icon in glob(os.path.join(icons_dir, '*.png')):
      m = re.search(r'^(.+)-([0-9]+)\.png', os.path.basename(icon))
      if m:
        name = '{0}.png'.format(m.group(1))
        size = m.group(2)
        icon_dir = os.path.join('build', 'icons', 'hicolor', '{0}x{0}'.format(size), 'apps')
        if not os.path.exists(icon_dir):
          os.makedirs(icon_dir)
        shutil.copyfile(icon, os.path.join(icon_dir, name))
    svg_icon_dir = os.path.join('build', 'icons', 'hicolor', 'scalable', 'apps')
    for icon in glob(os.path.join(icons_dir, '*.svg')):
      if not os.path.exists(svg_icon_dir):
        os.makedirs(svg_icon_dir)
      shutil.copyfile(icon, os.path.join(svg_icon_dir, os.path.basename(icon)))


class build(build_class):
  """
  Add 'build_trans' as a sub-command.
  """
  sub_commands = build_class.sub_commands + [('build_trans', None), ('build_icons', None)]


class install_data(install_data_class):
  """
  Install custom data, like .mo files and icons.
  """
  def run(self):
    po_dir = os.path.join('resources', 'po')
    for pot_name in [os.path.basename(filename)[:-4] for filename in glob(os.path.join(po_dir, '*.pot'))]:
      for lang in os.listdir(os.path.join('build', 'locale')):
        lang_dir = os.path.join('share', 'locale', lang, 'LC_MESSAGES')
        lang_file = os.path.join('build', 'locale', lang, 'LC_MESSAGES', '{0}.mo'.format(pot_name))
        self.data_files.append((lang_dir, [lang_file]))
    app_files = glob(os.path.join('build', '*.desktop'))
    if app_files:
      self.data_files.append((os.path.join('share', 'applications'), app_files))
    for icon in glob(os.path.join('build', 'icons', 'hicolor', '*', '*', '*')):
      icon_dest = os.path.join('share', os.path.dirname(os.path.dirname(icon[::-1])[::-1]))  # replace build with share
      self.data_files.append((icon_dest, [icon]))
    doc_dir = os.path.join('doc', '{0}-{1}'.format(MODULE_NAME, find_version(MODULE_NAME)))
    self.data_files.append((doc_dir, glob(os.path.join('docs', '*'))))
    self.data_files.append((os.path.join('share', MODULE_NAME), glob(os.path.join('resources', 'efi', '*'))))
    print('data_files', self.data_files)
    install_data_class.run(self)


class install(install_class):
  """
  Hack for having install_data run even if there is no data listed.
  """
  def initialize_options(self):
    install_class.initialize_options(self)
    self.distribution.has_data_files = lambda: True
    if not self.distribution.data_files:
      self.distribution.data_files = []

config = {
  'name': 'BootSetup',
  'description': 'Helps installing a bootloader like LiLo or Grub2 on your computer',
  'long_description': read('README.rst'),
  'license': find_info('license', MODULE_NAME),
  'author': find_info('credits', MODULE_NAME),
  'author_email': find_info('email', MODULE_NAME),
  'version': find_version(MODULE_NAME),
  'url': 'https://github.com/jrd/bootsetup/',
  'download_url': 'https://github.com/jrd/bootsetup/archive/master.zip',
  'packages': [MODULE_NAME],
  'include_package_data': True,
  'package_data': {MODULE_NAME: ['*.glade', '*.png']},
  'entry_points': {'console_scripts': ['bootsetup = {0}.bootsetup:main'.format(MODULE_NAME)]},
  'cmdclass': {'build': build, 'build_trans': build_trans, 'build_icons': build_icons, 'install': install, 'install_data': install_data},
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
