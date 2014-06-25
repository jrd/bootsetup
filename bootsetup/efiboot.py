#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
EFIBoot: common EFI Boot methods.
"""
from __future__ import unicode_literals, print_function, division, absolute_import

import codecs
import libsalt as slt


class EFIBoot(object):
  isTest = False
  secure_boot = False
  _efiPartition = None

  def __init__(self, isTest, secure_boot):
    self.isTest = isTest
    self.secure_boot = secure_boot

  def _debug(self, msg, *args):
    if self.isTest:
      if args:
        msg = "Debug: {0} {1}".format(msg, " ".join(args))
      else:
        msg = "Debug: {0}".format(msg)
      print(msg)
      with codecs.open("bootsetup.log", "a+", "utf-8") as fdebug:
        fdebug.write("{0}\n".format(msg))

  def _mountEfiPartition(self):
    """
    Return the mount point
    """
    if self._efiPartition:
      self._debug("efiPartition =", self._efiPartition)
      if slt.isMounted(self._efiPartition):
        self._debug("efiPartition already mounted")
        mp = slt.getMountPoint(self._efiPartition)
      else:
        self._debug("efiPartition not mounted")
        mp = slt.mountDevice(self._efiPartition)
      if mp:
        self._mountEfiInPartition(mp)
      return mp
    else:
      return None
