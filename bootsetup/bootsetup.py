#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
BootSetup helps installing LiLo or Grub2 on your computer.
This is the launcher.
"""
from __future__ import unicode_literals, print_function, division, absolute_import

from .__init__ import __app__, __copyright__, __author__, __license__, __version__

import abc
import os
import sys
import gettext


class BootSetup:

  __metaclass__ = abc.ABCMeta

  def __init__(self, appName, bootloader, targetPartition, isTest, useTestData):
    self._appName = appName
    self._bootloader = bootloader
    self._targetPartition = targetPartition
    self._isTest = isTest
    self._useTestData = useTestData
    print("BootSetup v{ver}".format(ver=__version__))

  @abc.abstractmethod
  def run_setup(self):
    """
    Launch the UI, exit at the end of the program
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def info_dialog(self, message, title=None, parent=None):
    """
    Displays an information message.

    """
    raise NotImplementedError()

  @abc.abstractmethod
  def error_dialog(self, message, title=None, parent=None):
    """
    Displays an error message.
    """
    raise NotImplementedError()


def usage():
  print("""BootSetup v{ver}
{copyright}
{license}
{author}

  bootsetup.py [--help] [--version] [--test [--data]] [bootloader] [partition]

Parameters:
  --help: Show this help message
  --version: Show the BootSetup version
  --test: Run it in test mode
    --data: Run it with some pre-filled data
  bootloader: could be lilo or grub2, by default nothing is proposed. You could use "_" to tell it's undefined.
  partition: target partition to install the bootloader.
    The disk of that partition is, by default, where the bootloader will be installed
    The partition will be guessed by default if not specified:
      ⋅ First Linux selected partition of the selected disk for LiLo.
      ⋅ First Linux partition, in order, of the selected disk for Grub2. This could be changed in the UI.
""".format(ver=__version__, copyright=__copyright__, license=__license__, author=__author__))


def print_err(*args):
  sys.stderr.write((' '.join(map(unicode, args)) + "\n").encode('utf-8'))


def die(s, exit=1):
  print_err(s)
  if exit:
    sys.exit(exit)


def find_locale_dir():
  if '.local' in __file__:
    return os.path.expanduser(os.path.join('~', '.local', 'share', 'locale'))
  else:
    return os.path.join('usr', 'share', 'locale')


def main(args=sys.argv[1:]):
  if os.path.dirname(__file__):
    os.chdir(os.path.dirname(__file__))
  is_graphic = bool(os.environ.get('DISPLAY'))
  is_test = False
  use_test_data = False
  bootloader = None
  target_partition = None
  gettext.install(domain=__app__, localedir=find_locale_dir(), unicode=True)
  for arg in args:
    if arg:
      if arg == '--help':
        usage()
        sys.exit(0)
      elif arg == '--version':
        print(__version__)
        sys.exit(0)
      elif arg == '--test':
        is_test = True
        print_err("*** Testing mode ***")
      elif is_test and arg == '--data':
        use_test_data = True
        print_err("*** Test data mode ***")
      elif arg[0] == '-':
        die(_("Unrecognized parameter '{0}'.").format(arg))
      else:
        if bootloader is None:
          bootloader = arg
        elif target_partition is None:
          target_partition = arg
        else:
          die(_("Unrecognized parameter '{0}'.").format(arg))
  if bootloader not in ('lilo', 'grub2', '_', None):
    die(_("bootloader parameter should be lilo, grub2 or '_', given {0}.").format(bootloader))
  if bootloader == '_':
    bootloader = None
  if target_partition and not os.path.exists(target_partition):
    die(_("Partition {0} not found.").format(target_partition))
  if is_graphic:
    from .bootsetup_gtk import BootSetupGtk as BootSetupImpl
  else:
    from .bootsetup_curses import BootSetupCurses as BootSetupImpl
  bootsetup = BootSetupImpl(__app__, bootloader, target_partition, is_test, use_test_data)
  bootsetup.run_setup()


if __name__ == '__main__':
  main()
