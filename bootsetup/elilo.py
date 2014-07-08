#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
ELiLo for BootSetup.
"""
from __future__ import unicode_literals, print_function, division, absolute_import

import sys
import tempfile
import shutil
import os
import glob
import libsalt as slt
from .efiboot import EFIBoot


class ELilo(EFIBoot):
  _prefix = None
  _tmp = None
  _partitions = None
  _cfgTemplate = """# ELILO configuration file
# Generated by BootSetup
chooser=textmenu
prompt
timeout=50
append = "vt.default_utf8=1 "
read-only
"""

  def __init__(self, isTest, secure_boot):
    super(self.__class__, self).__init__(isTest, secure_boot)
    self._prefix = "bootsetup.elilo-"
    self._tmp = tempfile.mkdtemp(prefix=self._prefix)
    slt.mounting._tempMountDir = os.path.join(self._tmp, 'mounts')
    self._debug("tmp dir =", self._tmp)

  def __del__(self):
    if self._tmp and os.path.exists(self._tmp):
      self._debug("cleanning", self._tmp)
      try:
        cfgPath = self.getConfigurationPath()
        if os.path.exists(cfgPath):
          self._debug("Remove", cfgPath)
          os.remove(cfgPath)
        if os.path.exists(slt.mounting._tempMountDir):
          self._debug("Remove", slt.mounting._tempMountDir)
          os.rmdir(slt.mounting._tempMountDir)
        self._debug("Remove", self._tmp)
        os.rmdir(self._tmp)
      except:
        pass

  def getConfigurationPath(self):
    return os.path.join(self._tmp, "elilo.conf")

  def _mountPartitions(self, mountPointList):
    """
    Fill a list of mount points for each partition
    """
    if self._partitions:
      partitionsToMount = [p for p in self._partitions if p[2] == "linux"]
      self._debug("mount partitions:", unicode(partitionsToMount))
      for p in partitionsToMount:
        dev = os.path.join("/dev", p[0])
        self._debug("mount partition", dev)
        if slt.isMounted(dev):
          mp = slt.getMountPoint(dev)
        else:
          mp = slt.mountDevice(dev)
        self._debug("mount partition", dev, "=>", unicode(mp))
        if mp:
          mountPointList[p[0]] = mp
          self._mountBootInPartition(mp)
        else:
          raise Exception("Cannot mount {d}".format(d=dev))

  def _umountAll(self, mountPoint, mountPointList):
    self._debug("umountAll")
    if mountPoint:
      if mountPointList:
        self._debug("umount other mount points:", unicode(mountPointList))
        for mp in mountPointList.values():
          if mp == mountPoint:
            continue  # skip it, will be unmounted just next
          self._debug("umount", unicode(mp))
          slt.umountDevice(mp)
      if mountPoint != '/':
        self._debug("main mount point ≠ '/' → umount", mountPoint)
        slt.umountDevice(mountPoint)

  def _createELiloSections(self, efiMountPoint, mountPointList):
    """
    Return a list of lilo section string for each partition.
    There could be more section than partitions if there are multiple kernels.
    """
    sections = []
    if self._partitions:
      for p in self._partitions:
        device = os.path.join("/dev", p[0])
        fs = p[1]
        bootType = p[2]
        label = p[3]
        if bootType == 'linux':
          mp = mountPointList[p[0]]
          sections.extend(self._getLinuxELiloSections(efiMountPoint, device, fs, mp, label))
        else:
          sys.err.write("The boot type {type} is not supported.\n".format(type=bootType))
    return sections

  def _getLinuxELiloSections(self, efiMountPoint, device, fs, mp, label):
    """
    Returns a list of string sections, one for each kernel+initrd
    """
    sections = []
    self._debug("Section 'linux' for", device, "/", fs, "mounted on", mp, "with label:", label)
    kernelList = sorted(glob.glob("{mp}/boot/vmlinuz*".format(mp=mp)))
    initrdList = sorted(glob.glob("{mp}/boot/initr*".format(mp=mp)))
    for l in (kernelList, initrdList):
      for el in l:
        if os.path.isdir(el) or os.path.islink(el):
          l.remove(el)
    self._debug("kernelList:", unicode(kernelList))
    self._debug("initrdList:", unicode(initrdList))
    uuid = slt.execGetOutput(['/sbin/blkid', '-s', 'UUID', '-o', 'value', device], shell=False)
    if uuid:
      rootDevice = "/dev/disk/by-uuid/{uuid}".format(uuid=uuid[0])
    else:
      rootDevice = device
    self._debug("rootDevice =", rootDevice)
    for (k, i, l) in self._getKernelInitrdCouples(kernelList, initrdList, label):
      self._debug("kernel, initrd, label found:", unicode(k), ",", unicode(i), ",", unicode(l))
      section = None
      if i:
        section = """# {label} Linux section
image=/EFI/Linux/{image}
  initrd=/EFI/Linux/{initrd}
  root={root}
""".format(image=k, initrd=i, root=rootDevice, label=l)
      else:
        section = """# {label} Linux section
image=/EFI/Linux/{image}
  root={root}
""".format(image=k, root=rootDevice, label=l)
      if fs == 'ext4':
        section += '  append="{append} "\n'.format(append='rootfstype=ext4')
      section += "  label={label}\n".format(label=l)
      sections.append(section)
    return sections

  def _getKernelInitrdCouples(self, kernelList, initrdList, labelRef):
    ret = []
    if kernelList:
      if len(kernelList) == 1:
        initrd = None
        if initrdList:
          initrd = initrdList[0]  # assume the only initrd match the only kernel
        ret.append([kernelList[0], initrd, labelRef])
      else:
        labelBase = labelRef[0:15 - 2] + "-"
        n = 0
        for kernel in kernelList:
          n += 1
          kernelSuffix = os.path.basename(kernel).replace("vmlinuz", "")
          initrd = None
          for i in initrdList:
            if kernelSuffix in i:  # find the matching initrd
              initrd = i
              break
          ret.append((kernel, initrd, labelBase + unicode(n)))
    return ret

  def createConfiguration(self, mbrDevice, efiPartition, bootPartition, partitions):
    """
    partitions format: [device, filesystem, boot type, label]
    """
    self._efiPartition = os.path.join(os.path.sep, 'dev', efiPartition)
    self._partitions = partitions
    self._debug("partitions:", unicode(self._partitions))
    mp = None
    mpList = None
    try:
      mp = self._mountEfiPartition()
      if not mp:
        raise Exception("Cannot mount the main EFI partition.")
      self._debug("mp =", unicode(mp))
      mpList = {}
      self._mountPartitions(mpList)
      self._debug("mount point lists:", unicode(mpList))
      eliloSections = self._createELiloSections(mp, mpList)
      self._debug("elilo sections:", unicode(eliloSections))
      f = open(self.getConfigurationPath(), "w")
      f.write(self._cfgTemplate)
      for s in eliloSections:
        f.write(s)
        f.write("\n")
      f.close()
    finally:
      self._umountAll(mp, mpList)

  def install(self):
    """
    Assuming that last configuration editing didn't modified mount point.
    """
    if self._mbrDevice:
      mp = None
      mpList = None
      try:
        mp = self._mountEfiPartition()
        if not mp:
          raise Exception("Cannot mount the main EFI partition.")
        self._debug("mp =", unicode(mp))
        mpList = {}
        self._mountPartitions(mpList)
        self._debug("mount point lists:", unicode(mpList))
        # copy the kernel + initrd + configuration to the EFI partition
        try:
          self._debug("create EFI/Boot directory in", mp)
          os.makedirs(os.path.join(mp, 'EFI', 'Boot'))
        except os.error:
          pass
        try:
          self._debug("create EFI/Linux directory in", mp)
          os.makedirs(os.path.join(mp, 'EFI', 'Linux'))
        except os.error:
          pass
        eliloBin = 'elilo-x86_64.efi'
        if self.secure_boot:
          destFile = 'loader.efi'
        else:
          destFile = 'bootx64.efi'
        self._debug("copy {0} to /EFI/Boot/{1}".format(eliloBin, destFile))
        shutil.copyfile(os.path.join(os.path.sep, 'boot', eliloBin), os.path.join(mp, 'EFI', 'Boot', destFile))
        self._debug("copy elilo.conf to /EFI/Boot/elilo.conf")
        shutil.copyfile(self.getConfigurationPath(), os.path.join(mp, 'EFI', 'Boot', 'elilo.conf'))
        if self.secure_boot:
          self._debug("install PreLoader for secure boot")
          for f, dest in (('HashTool.efi', 'HashTool.efi'), ('KeyTool.efi', 'KeyTool.efi'), ('PreLoader.efi', 'bootx64.efi'), ('shellx64.efi', 'shellx64.efi')):
            shutil.copyfile(os.path.join(os.path.sep, 'usr', 'share', 'bootsetup', f), os.path.join(mp, 'EFI', 'Boot', dest))
      finally:
        self._umountAll(mp, mpList)