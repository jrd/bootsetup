#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
Config class helps storing the configuration for the bootloader setup.
"""
from __future__ import unicode_literals, print_function, division, absolute_import

import sys
import re
import codecs
import os
from glob import glob
import libsalt as slt
from .efi import EFI


class Config(object):
  """
  Configuration for BootSetup.
  Available variables are:
  - disks  --  list of disks in the system. Format ["device", "format", "name (size)"]
  - partitions  --  list of partitions in the system. Format ["device", "fs type", "label (size)"]
  - boot_partitions  --  restricted list of partitions with bootable OS. Determined by os-prober. Format ["device", "fs type", "boot type", "OS", "label"]
  - efi_firmware  -- true if an EFI firmware has been loaded, thus indicated that the OS has boot in EFI mode.
  - esp  -- restricted list of ESP partitions. Format ["device", "fs type", "label (size")]
  - is_test  -- true if in Test Mode.
  - use_test_data  -- true if some Test Data will be used instead of real system data.
  - is_live  --  true if in a SaLT Live environment.
  - target_partition  -- target device (prefixed with /dev/) where the root OS will be (or is) installed.
  - cur_root_partition  --  target root partition, where to find binaries and /etc config files, determined from target_partition or from /
  - cur_bootmode  --  bios or efi, efi is available if efi_firmware is true and if esp is not empty
  - cur_bootloader  --  lilo, grub2, grub2_efi, elilo, gummiboot
  - cur_mbr_device  --  for bios mode, where to install first stage, determined from cur_root_partition
  - cur_esp  --  for efi mode, where to install the bootloader efi application, determined from cur_root_partition and esp
  - secure_boot  --  true if EFI application should be Secure Boot aware.
  """
  disks = []
  partitions = []
  boot_partitions = []
  efi_firmware = False
  esp = []
  is_test = False
  use_test_data = False
  is_live = False  # true if in a SaLT Live environment.
  target_partition = None
  cur_root_partition = None  # target root partition, where to find binaries and /etc config files, determined from target_partition or from /
  cur_bootmode = None  # bios or efi, efi is available if /sys/firmware/efi exists and esp is not empty
  cur_bootloader = None  # lilo, grub2, grub2_efi, elilo, gummiboot
  cur_mbr_device = None  # for bios mode, where to install first stage, determined from cur_root_partition
  cur_esp = None  # for efi mode, where to install the bootloader efi application, determined from cur_root_partition and esp
  secure_boot = False

  def __init__(self, is_test, use_test_data, target_partition=None):
    self._efi = EFI(is_test)
    self.is_test = is_test
    self.use_test_data = use_test_data
    self.target_partition = target_partition
    self._get_current_config()

  def __debug(self, msg, *args):
    if self.is_test:
      if args:
        msg = "Debug: {0} {1}".format(msg, " ".join(args))
      else:
        msg = "Debug: {0}".format(msg)
      print(msg)
      with codecs.open("bootsetup.log", "a+", "utf-8") as fdebug:
        fdebug.write("{0}\n".format(msg))

  def _get_current_config(self):
    print('Gathering current configuration…', end='')
    if self.is_test:
      print('')
    sys.stdout.flush()
    if self.is_test:
      self.is_live = False
    else:
      self.is_live = slt.isSaLTLiveEnv()
    if self.use_test_data:
      self.disks = [
        ['sda', 'msdos', 'WDC100 (100GB)'],
        ['sdb', 'gpt', 'SGT350 (350GB)']
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
      self.efi_firmware = True
      self.esp = [
        ['sda2', 'fat32', 'EFI System partition (100MB)']
      ]
      self.secure_boot = True
    else:
      self.disks = []
      self.partitions = []
      for disk_device in slt.getDisks():
        di = slt.getDiskInfo(disk_device)
        self.disks.append([disk_device, di['type'], "{0} ({1})".format(di['model'], di['sizeHuman'])])
        for p in slt.getPartitions(disk_device):
          pi = slt.getPartitionInfo(p)
          self.partitions.append([p, pi['fstype'], "{0} ({1})".format(pi['label'], pi['sizeHuman'])])
      self.boot_partitions = []
      probes = []
      if not self.is_live:
        # os-prober doesn't want to probe for /
        slashDevice = slt.execGetOutput(r"readlink -f $(df / | tail -n 1 | cut -d' ' -f1)")[0]
        slashFS = slt.getFsType(re.sub(r'^/dev/', '', slashDevice))
        osProbesPath = None
        for p in ("/usr/lib64/os-probes/mounted/90linux-distro", "/usr/lib/os-probes/mounted/90linux-distro"):
          if os.path.exists(p):
            osProbesPath = p
            break
        if osProbesPath:
          try:
            os.remove("/var/lib/os-prober/labels")  # ensure there is no previous labels
          except:
            pass
          self.__debug("Root device {0} ({1})".format(slashDevice, slashFS))
          self.__debug(osProbesPath + " " + slashDevice + " / " + slashFS)
          slashDistro = slt.execGetOutput([osProbesPath, slashDevice, '/', slashFS])
          if slashDistro:
            probes = slashDistro
      self.__debug("Probes: " + unicode(probes))
      osProberPath = None
      for p in ('/usr/bin/os-prober', '/usr/sbin/os-prober'):
        if os.path.exists(p):
          osProberPath = p
          break
      if osProberPath:
        probes.extend(slt.execGetOutput(osProberPath, shell=False))
      self.__debug("Probes: " + unicode(probes))
      for probe in probes:
        probe = unicode(probe).strip()  # ensure clean line
        if probe[0] != '/':
          continue
        probe_info = probe.split(':')
        probe_dev = re.sub(r'/dev/', '', probe_info[0])
        probe_os = probe_info[1]
        probe_label = probe_info[2]
        probe_boottype = probe_info[3]
        if probe_boottype == 'efi':  # skip efi entry
          continue
        try:
          probe_fstype = [p[1] for p in self.partitions if p[0] == probe_dev][0]
        except IndexError:
          probe_fstype = ''
        self.boot_partitions.append([probe_dev, probe_fstype, probe_boottype, probe_os, probe_label])
      self.efi_firmware = self._efi.has_efi_firmware()
      self.efi_firmware = False  # TODO disabled for salix live alpha
      for esp in self._efi.find_efi_partitions():
        esp = esp.replace('/dev/', '')
        # reuse information from self.partitions to complete the list
        for p in self.partitions:
          if p[0] == esp:
            self.esp.append(p)
            break
        else:
          self.esp.append([esp, '', ''])
      self.esp = []  # TODO disabled for salix live alpha
      self.secure_boot = self.efi_firmware and bool(self.esp)
      # guess cur_root_partition, cur_mbr_device and cur_esp from target_partition argument or environment.
      if self.is_live:
        if self.target_partition:
          self.cur_root_partition = re.sub(r'^/dev/', r'', self.target_partition)
      else:
        if self.target_partition:
          self.cur_root_partition = re.sub(r'^/dev/', r'', self.target_partition)
        else:
          try:
            dev = os.stat('/').st_dev
            majorMinor = '{0}:{1}'.format(os.major(dev), os.minor(dev))
            self.cur_root_partition = [os.path.basename(os.path.dirname(f)) for f in glob('/sys/class/block/*/dev') if open(f).read().strip() == majorMinor][0]
          except:
            pass
      if self.cur_root_partition:
        self.cur_mbr_device = re.sub(r'[0-9]+$', '', self.cur_root_partition)
        for p in sorted(self.esp):
          if re.match(r'^{0}[0-9]+$'.format(self.cur_mbr_device), p[0]):
            self.cur_esp = p[0]
            break
    print(' Done')
    sys.stdout.flush()

  def have_esp(self):
    return bool(self.esp)

  def __str__(self):
    s = """BootSetup Config
disks:{disks}
partitions:{partitions}
possible boot partitions:{boot_partitions}
possible efi system partitions:{esp}
""".format(disks="\n - " + "\n - ".join(map(" ".join, self.disks)), partitions="\n - " + "\n - ".join(map(" ".join, self.partitions)), boot_partitions="\n - " + "\n - ".join(map(" ".join, self.boot_partitions)), esp="\n - " + "\n - ".join(map(" ".join, self.esp)))
    s += """
target_partition:{target_partition}
cur_root_partition:{cur_root_partition}
cur_bootmode:{cur_bootmode}
cur_bootloader:{cur_bootloader}
cur_mbr_device:{cur_mbr_device}
cur_esp:{cur_esp}
secure_boot:{secure_boot}
""".format(target_partition=self.target_partition, cur_root_partition=self.cur_root_partition, cur_bootmode=self.cur_bootmode, cur_bootloader=self.cur_bootloader, cur_mbr_device=self.cur_mbr_device, cur_esp=self.cur_esp, secure_boot=self.secure_boot)
    return s
