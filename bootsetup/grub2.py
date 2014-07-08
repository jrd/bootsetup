#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
Grub2 for BootSetup.
"""
from __future__ import unicode_literals, print_function, division, absolute_import

import tempfile
import os
import sys
from collections import namedtuple
import libsalt as slt
from .efiboot import EFIBoot


class Grub2(EFIBoot):
  _prefix = None
  _tmp = None
  _bootInBootMounted = False
  _procInBootMounted = False

  def __init__(self, isTest, secure_boot=False):
    super(self.__class__, self).__init__(isTest, secure_boot)
    self._prefix = "bootsetup.grub2-"
    self._tmp = tempfile.mkdtemp(prefix=self._prefix)
    slt.mounting._tempMountDir = os.path.join(self._tmp, 'mounts')
    self._debug("tmp dir =", self._tmp)

  def __del__(self):
    if self._tmp and os.path.exists(self._tmp):
      self._debug("cleanning", self._tmp)
      try:
        if os.path.exists(slt.mounting._tempMountDir):
          self._debug("Remove", slt.mounting._tempMountDir)
          os.rmdir(slt.mounting._tempMountDir)
        self._debug("Remove", self._tmp)
        os.rmdir(self._tmp)
      except:
        pass

  @staticmethod
  def checkout_grub2_config(root_partition):
    partition = os.path.join(os.path.sep, 'dev', root_partition)
    if slt.isMounted(partition):
      mp = slt.getMountPoint(partition)
      doumount = False
    else:
      mp = slt.mountDevice(partition)
      doumount = True
    if not mp:
      return None
    grub2cfg = os.path.join(mp, 'etc', 'default', 'grub')
    if os.path.exists(grub2cfg):
      return namedtuple('Grub2Config', 'cfg mp doumount')(grub2cfg, mp, doumount)
    else:
      return None

  @staticmethod
  def release_grub2_config(grub2cfgInfo):
    if grub2cfgInfo.doumount:
      slt.umountDevice(grub2cfgInfo.mp)

  @staticmethod
  def is_grub2_available(root_partition):
    return False  # TODO disabled for salix live alpha
    grub2config = Grub2.checkout_grub2_config(root_partition)
    if grub2config:
      Grub2.release_grub2_config(grub2config)
      return True
    else:
      return False

  def _mountBootPartition(self, bootPartition):
    """
    Return the mount point
    """
    self._debug("bootPartition =", bootPartition)
    if slt.isMounted(bootPartition):
      self._debug("bootPartition already mounted")
      return slt.getMountPoint(bootPartition)
    else:
      self._debug("bootPartition not mounted")
      return slt.mountDevice(bootPartition)

  def _mountBootInBootPartition(self, mountPoint):
    # assume that if the mount_point is /, any /boot directory is already accessible/mounted
    if mountPoint != '/' and os.path.exists(os.path.join(mountPoint, 'etc/fstab')):
      self._debug("mp != / and etc/fstab exists, will try to mount /boot by chrooting")
      try:
        self._debug("grep -q /boot {mp}/etc/fstab && chroot {mp} /sbin/mount /boot".format(mp=mountPoint))
        if slt.execCall("grep -q /boot {mp}/etc/fstab && chroot {mp} /sbin/mount /boot".format(mp=mountPoint)):
          self._debug("/boot mounted in", mountPoint)
          self._bootInBootMounted = True
      except:
        pass

  def _bindProcSysDev(self, mountPoint):
    """
    bind /proc /sys and /dev into the boot partition
    """
    if mountPoint != "/":
      self._debug("mount point ≠ / so mount /dev, /proc and /sys in", mountPoint)
      self._procInBootMounted = True
      slt.execCall('mount -o bind /dev {mp}/dev'.format(mp=mountPoint))
      slt.execCall('mount -o bind /proc {mp}/proc'.format(mp=mountPoint))
      slt.execCall('mount -o bind /sys {mp}/sys'.format(mp=mountPoint))

  def _unbindProcSysDev(self, mountPoint):
    """
    unbind /proc /sys and /dev into the boot partition
    """
    if self._procInBootMounted:
      self._debug("mount point ≠ / so umount /dev, /proc and /sys in", mountPoint)
      slt.execCall('umount {mp}/dev'.format(mp=mountPoint))
      slt.execCall('umount {mp}/proc'.format(mp=mountPoint))
      slt.execCall('umount {mp}/sys'.format(mp=mountPoint))

  def _copyAndInstallGrub2(self, mountPoint, device):
    if self.isTest:
      self._debug("/usr/sbin/grub-install --boot-directory {bootdir} --no-floppy {dev}".format(bootdir=os.path.join(mountPoint, "boot"), dev=device))
      return True
    else:
      return slt.execCall("/usr/sbin/grub-install --boot-directory {bootdir} --no-floppy {dev}".format(bootdir=os.path.join(mountPoint, "boot"), dev=device))

  def _installGrub2Config(self, mountPoint):
    if os.path.exists(os.path.join(mountPoint, 'etc/default/grub')) and os.path.exists(os.path.join(mountPoint, 'usr/sbin/update-grub')):
      self._debug("grub2 package is installed on the target partition, so it will be used to generate the grub.cfg file")
      # assume everything is installed on the target partition, grub2 package included.
      if self.isTest:
        self._debug("chroot {mp} /usr/sbin/update-grub".format(mp=mountPoint))
      else:
        slt.execCall("chroot {mp} /usr/sbin/update-grub".format(mp=mountPoint))
    else:
      self._debug("grub2 not installed on the target partition, so grub_mkconfig will directly be used to generate the grub.cfg file")
      # tiny OS installed on that mount point, so we cannot chroot on it to install grub2 config.
      if self.isTest:
        self._debug("/usr/sbin/grub-mkconfig -o {cfg}".format(cfg=os.path.join(mountPoint, "boot/grub/grub.cfg")))
      else:
        slt.execCall("/usr/sbin/grub-mkconfig -o {cfg}".format(cfg=os.path.join(mountPoint, "boot/grub/grub.cfg")))

  def _umountAll(self, mountPoint):
    self._debug("umountAll")
    if mountPoint:
      self._debug("umounting main mount point", mountPoint)
      self._unbindProcSysDev(mountPoint)
      if self._bootInBootMounted:
        self._debug("/boot mounted in", mountPoint, "so umount it")
        slt.execCall("chroot {mp} /sbin/umount /boot".format(mp=mountPoint))
      if mountPoint != '/':
        self._debug("umain mount point ≠ '/' → umount", mountPoint)
        slt.umountDevice(mountPoint)
    self._bootInBootMounted = False
    self._procInBootMounted = False

  def install(self, mbrDevice, bootPartition):
    mbrDevice = os.path.join("/dev", mbrDevice)
    bootPartition = os.path.join("/dev", bootPartition)
    self._debug("mbrDevice =", mbrDevice)
    self._debug("bootPartition =", bootPartition)
    self._bootInBootMounted = False
    self._procInBootMounted = False
    mp = None
    try:
      mp = self._mountBootPartition(bootPartition)
      self._debug("mp =", unicode(mp))
      self._mountBootInBootPartition(mp)
      if self._copyAndInstallGrub2(mp, mbrDevice):
        self._installGrub2Config(mp)
      else:
        sys.stderr.write("Grub2 cannot be installed on this disk [{0}]\n".format(mbrDevice))
    finally:
      self._umountAll(mp)
