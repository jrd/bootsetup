#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set et ai sta sw=2 ts=2 tw=0:
"""
Config class helps storing the configuration for the bootloader setup.
"""
from __future__ import unicode_literals

__copyright__ = 'Copyright 2013-2014, Salix OS'
__license__ = 'GPL2+'

import sys
import re
import codecs
import os
import salix_livetools_library as sltl

class Config:
  """
  Configuration for BootSetup
  """
  disks = []
  partitions = []
  boot_partitions = []
  cur_bootloader = None
  cur_boot_partition = None
  cur_mbr_device = None
  is_test = False
  use_test_data = False
  is_live = False
  
  def __init__(self, bootloader, target_partition, is_test, use_test_data):
    self.cur_bootloader = bootloader
    self.cur_boot_partition = target_partition and re.sub(r'/dev/', '', target_partition) or ''
    self.cur_mbr_device = ''
    self.is_test = is_test
    self.use_test_data = use_test_data
    self._get_current_config()

  def __debug(self, msg):
    if self.is_test:
      print "Debug: " + msg
      with codecs.open("bootsetup.log", "a+", "utf-8") as fdebug:
        fdebug.write("Debug: {0}\n".format(msg))

  def _get_current_config(self):
    print 'Gathering current configuration…',
    if self.is_test:
      print ''
    sys.stdout.flush()
    if self.is_test:
      self.is_live = False
    else:
      self.is_live = sltl.isSaLTLiveEnv()
    if self.use_test_data:
      self.disks = [
            ['sda', 'WDC100 (100GB)'],
            ['sdb', 'SGT350 (350GB)']
          ]
      self.partitions = [
            ['sda1', 'ntfs', 'WinVista (20GB)'],
            ['sda5', 'ext2', 'Salix (80GB)'],
            ['sdb1', 'fat32', 'Data (300GB)'],
            ['sdb2', 'ext4', 'Debian (50GB)']
          ]
      self.boot_partitions = [
            ['sda5', 'ext2', 'linux', 'Salix', 'Salix 14.0'],
            ['sda1', 'ntfs', 'chain', 'Windows', 'Vista'],
            ['sdb2', 'ext4', 'linux', 'Debian', 'Debian 7']
          ]
      if not self.cur_boot_partition:
        self.cut_boot_partition = 'sda5'
    else:
      self.disks = []
      self.partitions = []
      for disk_device in sltl.getDisks():
        di = sltl.getDiskInfo(disk_device)
        self.disks.append([disk_device, "{0} ({1})".format(di['model'], di['sizeHuman'])])
        for p in sltl.getPartitions(disk_device):
          pi = sltl.getPartitionInfo(p)
          self.partitions.append([p, pi['fstype'], "{0} ({1})".format(pi['label'], pi['sizeHuman'])])
      self.boot_partitions = []
      probes = []
      if not self.is_live:
        # os-prober doesn't want to probe for /
        slashDevice = sltl.execGetOutput(r"readlink -f $(df / | tail -n 1 | cut -d' ' -f1)")[0]
        slashFS = sltl.getFsType(re.sub(r'^/dev/', '', slashDevice))
        osProbesPath = None
        for p in ("/usr/lib64/os-probes/mounted/90linux-distro", "/usr/lib/os-probes/mounted/90linux-distro"):
          if os.path.exists(p):
            osProbesPath = p
        if osProbesPath:
          self.__debug("Root device {0} ({1})".format(slashDevice, slashFS))
          self.__debug(osProbesPath + " " + slashDevice + " / " + slashFS)
          slashDistro = sltl.execGetOutput([osProbesPath, slashDevice, '/', slashFS])
          if slashDistro:
            probes = slashDistro
      self.__debug("Probes: " + unicode(probes))
      osProberPath = None
      for p in ('/usr/bin/os-prober', '/usr/sbin/os-prober'):
        if os.path.exists(p):
          osProberPath = p
      if osProberPath:
        probes.extend(sltl.execGetOutput(osProberPath, shell = False))
      self.__debug("Probes: " + unicode(probes))
      for probe in probes:
        probe = unicode(probe).strip() # ensure clean line
        if probe[0] != '/':
          continue
        probe_info = probe.split(':')
        probe_dev = re.sub(r'/dev/', '', probe_info[0])
        probe_os = probe_info[1]
        probe_label = probe_info[2]
        probe_boottype = probe_info[3]
        if probe_boottype == 'efi': # skip efi entry
          continue
        try:
          probe_fstype = [p[1] for p in self.partitions if p[0] == probe_dev][0]
        except IndexError:
          probe_fstype = ''
        self.boot_partitions.append([probe_dev, probe_fstype, probe_boottype, probe_os, probe_label])
    if self.cur_boot_partition:
      # use the disk of that partition.
      self.cur_mbr_device = re.sub(r'^(.+?)[0-9]*$', r'\1', self.cur_boot_partition)
    elif len(self.disks) > 0:
      # use the first disk.
      self.cur_mbr_device = self.disks[0][0]
    print ' Done'
    sys.stdout.flush()
