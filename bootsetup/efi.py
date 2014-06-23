#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
EFI tools.
"""
from __future__ import unicode_literals, print_function, division, absolute_import

import os
import codecs
import libsalt as slt
import pyreadpartitions as pyrp


class EFI:
  isTest = False
  _efi_type = "EFI System partition"

  def __init__(self, isTest):
    self.isTest = isTest

  def __debug(self, msg, *args):
    if self.isTest:
      if args:
        msg = "Debug: {0} {1}".format(msg, " ".join(args))
      else:
        msg = "Debug: {0}".format(msg)
      print(msg)
      with codecs.open("bootsetup.log", "a+", "utf-8") as fdebug:
        fdebug.write("{0}\n".format(msg))

  def has_efi_firmware(self):
    """
    Return true if /sys/firmware/efi exists
    """
    return os.path.exists(os.path.join('/', 'sys', 'firmware', 'efi'))

  def find_efi_partitions(self):
    """
    Return the EFI partitions (/dev/sdaX form) for each device/disk
    """
    esp = []
    for disk in slt.disk.getDisks():
      with open('/dev/{0}'.format(disk), 'rb') as fp:
        parts_info = pyrp.get_disk_partitions_info(fp)
        if parts_info.gpt and parts_info.gpt.partitions:
          for part in parts_info.gpt.partitions:
            if part.type == self._efi_type:
              esp.append('/dev/{0}{1}'.format(disk, part.index))
    return sorted(esp)
