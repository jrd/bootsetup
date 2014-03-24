#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set et ai sta sw=2 ts=2 tw=0:
"""
LiLo for BootSetup.
"""
from __future__ import unicode_literals

__copyright__ = 'Copyright 2013-2014, Salix OS'
__license__ = 'GPL2+'

import sys
import tempfile
import shutil
import os
import glob
import codecs
import salix_livetools_library as sltl
import subprocess
from operator import itemgetter

class Lilo:
  
  isTest = False
  _prefix = None
  _tmp = None
  _mbrDevice = None
  _bootPartition = None
  _partitions = None
  _bootsMounted = []
  _cfgTemplate = """# LILO configuration file
# Generated by BootSetup
#
# Start LILO global section
# Append any additional kernel parameters:
append = "vt.default_utf8=1 "
boot = {boot}
lba32
compact

# Boot BMP Image.
# Bitmap in BMP format: 640x480x8
bitmap = {mp}/boot/salix.bmp
# Menu colors (foreground, background, shadow, highlighted
# foreground, highlighted background, highlighted shadow):
bmp-colors = 255,20,255,20,255,20
# Location of the option table: location x, location y, number of
# columns, lines per column (max 15), "spill" this is how many
# entries must be in the first column before the next begins to
# be used.  We do not specify it here, as there is just one column.
bmp-table = 60,6,1,16
# Timer location x, timer location y, foreground color,
# background color, shadow color.
bmp-timer = 65,29,0,255

# Standard menu.
# Or, you can comment out the bitmap menu above and 
# use a boot message with the standard menu:
# message = /boot/boot_message.txt

# Wait until the timeout to boot (if commented out, boot the
# first entry immediately):
prompt
# Timeout before the first entry boots.
# This is given in tenths of a second, so 600 for every minute:
timeout = 50
# Override dangerous defaults that rewrite the partition table:
change-rules
reset

# Normal VGA console
# vga = normal
vga = {vga}
# End LILO global section
#
# BootSetup can be executed from a LiveCD. This means that lilo
# could be issued from a 'chrooted' Linux partition, which would
# happen to be the first Linux partition listed below.
# Therefore the following paths are relevant only when viewed
# from that 'chrooted' partition's perspective. Please take this
# constraint into consideration if you must modify this file
# or else BootSetup will fail.
#
# If later on you want to use this configuration file directly
# with lilo in a command line, use the following syntax:
# "lilo -v -C /etc/bootsetup/lilo.conf" instead of the traditional
# "lilo -v" command. You must of course issue that command from
# the operating system holding /etc/bootsetup/lilo.conf and ensure that
# all partitions referenced in it are mounted on the appropriate
# mountpoints.
"""

  def __init__(self, isTest):
    self.isTest = isTest
    self._prefix = "bootsetup.lilo-"
    self._tmp = tempfile.mkdtemp(prefix = self._prefix)
    sltl.mounting._tempMountDir = os.path.join(self._tmp, 'mounts')
    self.__debug("tmp dir = " + self._tmp)

  def __del__(self):
    if self._tmp and os.path.exists(self._tmp):
      self.__debug("cleanning " + self._tmp)
      try:
        cfgPath = self.getConfigurationPath()
        if os.path.exists(cfgPath):
          self.__debug("Remove " + cfgPath)
          os.remove(cfgPath)
        if os.path.exists(sltl.mounting._tempMountDir):
          self.__debug("Remove " + sltl.mounting._tempMountDir)
          os.rmdir(sltl.mounting._tempMountDir)
        self.__debug("Remove " + self._tmp)
        os.rmdir(self._tmp)
      except:
        pass

  def __debug(self, msg):
    if self.isTest:
      print "Debug: " + msg
      with codecs.open("bootsetup.log", "a+", "utf-8") as fdebug:
        fdebug.write("Debug: {0}\n".format(msg))

  def getConfigurationPath(self):
    return os.path.join(self._tmp, "lilo.conf")

  def _mountBootPartition(self):
    """
    Return the mount point
    """
    self.__debug("bootPartition = " + self._bootPartition)
    if sltl.isMounted(self._bootPartition):
      self.__debug("bootPartition already mounted")
      mp = sltl.getMountPoint(self._bootPartition)
    else:
      self.__debug("bootPartition not mounted")
      mp = sltl.mountDevice(self._bootPartition)
    if mp:
      self._mountBootInPartition(mp)
    return mp

  def _mountBootInPartition(self, mountPoint):
    # assume that if the mount_point is /, any /boot directory is already accessible/mounted
    fstab = os.path.join(mountPoint, 'etc/fstab')
    bootdir = os.path.join(mountPoint, 'boot')
    if mountPoint != '/' and os.path.exists(fstab) and os.path.exists(bootdir):
      self.__debug("mp != / and etc/fstab + boot exists, will try to mount /boot by reading fstab")
      try:
        self.__debug('set -- $(grep /boot {fstab}) && echo "$1,$3"'.format(fstab = fstab))
        (bootDev, bootType) = sltl.execGetOutput('set -- $(grep /boot {fstab}) && echo "$1,$3"'.format(fstab = fstab), shell = True)[0].split(',')
        if bootDev and not os.path.ismount(bootdir):
          mp = sltl.mountDevice(bootDev, fsType = bootType, mountPoint = bootdir)
          if mp:
            self._bootsMounted.append(mp)
            self.__debug("/boot mounted in " + mp)
      except:
        pass

  def _mountPartitions(self, mountPointList):
    """
    Fill a list of mount points for each partition
    """
    if self._partitions:
      partitionsToMount = [p for p in self._partitions if p[2] == "linux"]
      self.__debug("mount partitions: " + unicode(partitionsToMount))
      for p in partitionsToMount:
        dev = os.path.join("/dev", p[0])
        self.__debug("mount partition " + dev)
        if sltl.isMounted(dev):
          mp = sltl.getMountPoint(dev)
        else:
          mp = sltl.mountDevice(dev)
        self.__debug("mount partition " + dev + " => " + unicode(mp))
        if mp:
          mountPointList[p[0]] = mp
          self._mountBootInPartition(mp)
        else:
          raise Exception("Cannot mount {d}".format(d = dev))

  def _umountAll(self, mountPoint, mountPointList):
    self.__debug("umountAll")
    if mountPoint:
      for mp in self._bootsMounted:
        self.__debug("umounting " + unicode(mp))
        sltl.umountDevice(mp, deleteMountPoint = False)
      self._bootsMounted = []
      if mountPointList:
        self.__debug("umount other mount points: " + unicode(mountPointList))
        for mp in mountPointList.values():
          if mp == mountPoint:
            continue # skip it, will be unmounted just next
          self.__debug("umount " + unicode(mp))
          sltl.umountDevice(mp)
      if mountPoint != '/':
        self.__debug("main mount point ≠ '/' → umount " + mountPoint)
        sltl.umountDevice(mountPoint)

  def _createLiloSections(self, mountPointList):
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
        if bootType == 'chain':
          sections.append(self._getChainLiloSection(device, label))
        elif bootType == 'linux':
          mp = mountPointList[p[0]]
          sections.extend(self._getLinuxLiloSections(device, fs, mp, label))
        else:
          sys.err.write("The boot type {type} is not supported.\n".format(type = bootType))
    return sections

  def _getChainLiloSection(self, device, label):
    """
    Returns a string for a chainloaded section
    """
    self.__debug("Section 'chain' for " + device + " with label: " + label)
    return """# {label} chain section
  other = {device}
  label = {label}
""".format(device = device, label = label)

  def _getLinuxLiloSections(self, device, fs, mp, label):
    """
    Returns a list of string sections, one for each kernel+initrd
    """
    sections = []
    self.__debug("Section 'linux' for " + device + "/" + fs + ", mounted on " + mp + " with label: " + label)
    kernelList = sorted(glob.glob("{mp}/boot/vmlinuz*".format(mp = mp)))
    initrdList = sorted(glob.glob("{mp}/boot/initr*".format(mp = mp)))
    for l in (kernelList, initrdList):
      for el in l:
        if os.path.isdir(el) or os.path.islink(el):
          l.remove(el)
    self.__debug("kernelList: " + unicode(kernelList))
    self.__debug("initrdList: " + unicode(initrdList))
    uuid = sltl.execGetOutput(['/sbin/blkid', '-s', 'UUID', '-o', 'value', device], shell = False)
    if uuid:
      rootDevice = "/dev/disk/by-uuid/{uuid}".format(uuid = uuid[0])
    else:
      rootDevice = device
    self.__debug("rootDevice = " + rootDevice)
    for (k, i, l) in self._getKernelInitrdCouples(kernelList, initrdList, label):
      self.__debug("kernel, initrd, label found: " + unicode(k) + "," + unicode(i) + "," + unicode(l))
      section = None
      if i:
        section = """# {label} Linux section
  image = {image}
  initrd = {initrd}
  root = {root}
""".format(image = k, initrd = i, root = rootDevice, label = l)
      else:
        section = """# {label} Linux section
  image = {image}
  root = {root}
""".format(image = k, root = rootDevice, label = l)
      if fs == 'ext4':
        section += '  append = "{append} "\n'.format(append = 'rootfstype=ext4')
      section += "  read-only\n  label = {label}\n".format(label = l)
      sections.append(section)
    return sections

  def _getKernelInitrdCouples(self, kernelList, initrdList, labelRef):
    ret = []
    if kernelList:
      if len(kernelList) == 1:
        initrd = None
        if initrdList:
          initrd = initrdList[0] # assume the only initrd match the only kernel
        ret.append([kernelList[0], initrd, labelRef])
      else:
        labelBase = labelRef[0:15-2] + "-"
        n = 0
        for kernel in kernelList:
          n += 1
          kernelSuffix = os.path.basename(kernel).replace("vmlinuz", "")
          initrd = None
          for i in initrdList:
            if kernelSuffix in i: # find the matching initrd
              initrd = i
              break
          ret.append((kernel, initrd, labelBase + unicode(n)))
    return ret

  def _getFrameBufferConf(self):
    """
    Return the frame buffer configuration for this hardware.
    Format: (fb, label)
    """
    try:
      fbGeometry = sltl.execGetOutput("/usr/sbin/fbset | grep -w geometry")
    except subprocess.CalledProcessorError:
      self.__debug("Impossible to determine frame buffer mode, default to text.")
      fbGeometry = None
    mode = None
    label = None
    if fbGeometry:
      vesaModes = [
          (320, 200, 4, None),
          (640, 400, 4, None),
          (640, 480, 4, None),
          (800, 500, 4, None),
          (800, 600, 4, 770),
          (1024, 640, 4, None),
          (896, 672, 4, None),
          (1152, 720, 4, None),
          (1024, 768, 4, 772),
          (1440, 900, 4, None),
          (1280, 1024, 4, 774),
          (1400, 1050, 4, None),
          (1600, 1200, 4, None),
          (1920, 1200, 4, None),
          (320, 200, 8, None),
          (640, 400, 8, 768),
          (640, 480, 8, 769),
          (800, 500, 8, 879),
          (800, 600, 8, 771),
          (1024, 640, 8, 874),
          (896, 672, 8, 815),
          (1152, 720, 8, 869),
          (1024, 768, 8, 773),
          (1440, 900, 8, 864),
          (1280, 1024, 8, 775),
          (1400, 1050, 8, 835),
          (1600, 1200, 8, 796),
          (1920, 1200, 8, 893),
          (320, 200, 15, 781),
          (640, 400, 15, 801),
          (640, 480, 15, 784),
          (800, 500, 15, 880),
          (800, 600, 15, 787),
          (1024, 640, 15, 875),
          (896, 672, 15, 816),
          (1152, 720, 15, 870),
          (1024, 768, 15, 790),
          (1440, 900, 15, 865),
          (1280, 1024, 15, 793),
          (1400, 1050, 15, None),
          (1600, 1200, 15, 797),
          (1920, 1200, 15, None),
          (320, 200, 16, 782),
          (640, 400, 16, 802),
          (640, 480, 16, 785),
          (800, 500, 16, 881),
          (800, 600, 16, 788),
          (1024, 640, 16, 876),
          (896, 672, 16, 817),
          (1152, 720, 16, 871),
          (1024, 768, 16, 791),
          (1440, 900, 16, 866),
          (1280, 1024, 16, 794),
          (1400, 1050, 16, 837),
          (1600, 1200, 16, 798),
          (1920, 1200, 16, None),
          (320, 200, 24, 783),
          (640, 400, 24, 803),
          (640, 480, 24, 786),
          (800, 500, 24, 882),
          (800, 600, 24, 789),
          (1024, 640, 24, 877),
          (896, 672, 24, 818),
          (1152, 720, 24, 872),
          (1024, 768, 24, 792),
          (1440, 900, 24, 867),
          (1280, 1024, 24, 795),
          (1400, 1050, 24, 838),
          (1600, 1200, 24, 799),
          (1920, 1200, 24, None),
          (320, 200, 32, None),
          (640, 400, 32, 804),
          (640, 480, 32, 809),
          (800, 500, 32, 883),
          (800, 600, 32, 814),
          (1024, 640, 32, 878),
          (896, 672, 32, 819),
          (1152, 720, 32, 873),
          (1024, 768, 32, 824),
          (1440, 900, 32, 868),
          (1280, 1024, 32, 829),
          (1400, 1050, 32, None),
          (1600, 1200, 32, 834),
          (1920, 1200, 32, None),
        ]
      values = fbGeometry[0].strip().split(' ')
      self.__debug("FB Values: " + unicode(values))
      xRes = int(values[1])
      yRes = int(values[2])
      deep = int(values[-1])
      xMax = None
      yMax = None
      dMax = None
      # order the vesa modes by vertical size desc, horizontal size desc, color depth desc.
      for vesaMode in sorted(vesaModes, key = itemgetter(1, 0, 2), reverse = True):
        (x, y, d, m) = vesaMode
        if m:
          self.__debug("trying {0} for y, {1} for x and {2} for d".format(y, x, d))
          if y <= yRes and x <= xRes and d <= deep:
            xMax = x
            yMax = y
            dMax = d
            mode = m
            break
      if mode:
        self.__debug("Max mode found: {x}×{y}×{d}".format(x = xMax, y = yMax, d = dMax))
        label = "{x}x{y}x{d}".format(x = xMax, y = yMax, d = dMax)
    if not mode:
      mode = 'normal'
      label = 'text'
    return (mode, label)

  def createConfiguration(self, mbrDevice, bootPartition, partitions):
    """
    partitions format: [device, filesystem, boot type, label]
    """
    self._mbrDevice = os.path.join("/dev", mbrDevice)
    self._bootPartition = os.path.join("/dev", bootPartition)
    self._partitions = partitions
    self._bootsMounted = []
    self.__debug("partitions: " + unicode(self._partitions))
    mp = None
    mpList = None
    try:
      mp = self._mountBootPartition()
      if not mp:
        raise Exception("Cannot mount the main boot partition.")
      self.__debug("mp = " + unicode(mp))
      mpList = {}
      self._mountPartitions(mpList)
      self.__debug("mount point lists: " + unicode(mpList))
      liloSections = self._createLiloSections(mpList)
      self.__debug("lilo sections: " + unicode(liloSections))
      (fb, fbLabel) = self._getFrameBufferConf()
      self.__debug("frame buffer mode = " + unicode(fb) + " " + unicode(fbLabel))
      f = open(self.getConfigurationPath(), "w")
      f.write(self._cfgTemplate.format(boot = self._mbrDevice, mp = mp, vga = "{0} # {1}".format(fb, fbLabel)))
      for s in liloSections:
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
      self._bootsMounted = []
      mp = None
      mpList = None
      try:
        mp = self._mountBootPartition()
        if not mp:
          raise Exception("Cannot mount the main boot partition.")
        self.__debug("mp = " + unicode(mp))
        mpList = {}
        self._mountPartitions(mpList)
        self.__debug("mount point lists: " + unicode(mpList))
        # copy the configuration to the boot_partition
        try:
          self.__debug("create etc/bootsetup directory in " + mp)
          os.makedirs(os.path.join(mp, 'etc/bootsetup'))
        except os.error:
          pass
        self.__debug("copy lilo.conf to etc/bootsetup")
        shutil.copyfile(self.getConfigurationPath(), os.path.join(mp, '/etc/bootsetup/lilo.conf'))
        # run lilo
        if self.isTest:
          self.__debug('/sbin/lilo -t -v -C {mp}/etc/bootsetup/lilo.conf'.format(mp = mp))
          sltl.execCall('/sbin/lilo -t -v -C {mp}/etc/bootsetup/lilo.conf'.format(mp = mp))
        else:
          sltl.execCall('/sbin/lilo -C {mp}/etc/bootsetup/lilo.conf'.format(mp = mp))
      finally:
        self._umountAll(mp, mpList)
