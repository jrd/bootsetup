#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
Utility functions
"""
from __future__ import unicode_literals, print_function, division, absolute_import

import os
import re
import libsalt as slt


def mountPartition(partition):
  """
  partition is with the /dev/ prefix
  Return (mountPoint, shouldUmount) if succeeds, None otherwise.
  shouldUmount is True if the partition has been mounted and hence should be unmounted later.
  """
  mp = slt.getMountPoint(partition)
  if mp:
    umount = False
  else:
    mp = slt.mountDevice(partition)
    umount = True
  return (mp, umount)


def umountPartition(mountPartitionInfo):
  """
  mountPartitionInfo should be the same format as the result of mountPartition.
  """
  try:
    (mp, umount) = mountPartitionInfo
  except:
    raise Exception("mountPartitionInfo should be a tuple with the mount point and a boolean indicating if it should be unmounted")
  if umount:
    return slt.umountDevice(mp)
  else:
    return True


def readFstabMountPoints(fstabPath):
  """
  Return a list of mount point defined in fstab file
  """
  try:
    mpList = []
    with open(fstabPath, 'r') as f:
      for line in f.readlines():
        mp = re.sub(r'^[^ ]+ +([^ ]+) .*', r'\1', line)
        if mp and ' ' not in mp and mp[0] == '/':
          mpList.append(mp)
    return mpList
  except:
    return False


def existsInPartition(partition, filePath):
  """
  Return true if the filePath exists in the partition
  If you want to test for a directory, ends the path with a os.path.sep (/)
  """
  mpInfo = mountPartition(partition)
  if mpInfo:
    mp = mpInfo[0]
    exists = os.path.exists(os.path.join(mp, filePath))
    subMpList = []
    if mp != '/' and not exists and os.path.exists(os.path.join(mp, 'etc', 'fstab')):
      fstabMps = readFstabMountPoints(os.path.join(mp, 'etc', 'fstab'))
      absFilePath = os.path.realpath(os.path.join(os.path.sep, filePath))
      for fstabMp in fstabMps:
        if absFilePath.startswith(fstabMp):
          try:
            slt.execChroot(mp, ['mount', fstabMp])
            subMpList.append(fstabMp)
          except:
            pass
      # try to see if it exists now
      exists = os.path.exists(os.path.join(mp, filePath))
    # umount everything in reverse mounting order
    for subMp in subMpList[::-1]:
      try:
        slt.execChroot(mp, ['umount', subMp])
      except:
        pass
    umountPartition(mpInfo)
    return exists
  else:
    return False
