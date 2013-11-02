#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set et ai sta sw=2 ts=2 tw=0:
"""
LiLo for BootSetup.
"""
__copyright__ = 'Copyright 2013-2014, Salix OS'
__license__ = 'GPL2+'

import tempfile
import shutil
import os
import glob
import salix_livetools_library as sltl

class Lilo:
  
  def __init__(self):
    self._prefix = "bootsetup.lilo-"
    self._tmp = tempfile.mkdtemp(self._prefix)
    sltl.mounting._tempMountDir = os.path.join(self._tmp, 'mounts')

  def __del__(self):
    print "nettoyage lilo"
    if self._tmp and os.path.exists(self._tmp):
      shutil.rmtree(self._tmp)

  def getConfigurationPath(self):
    return os.path.join(self._tmp, "lilo.conf")

  def _mountBootPartition(self, boot_partition):
    """
    Return the mount point
    """
    if sltl.isMounted(boot_partition):
      return sltl.getMountPoint(boot_partition)
    else:
      return sltl.mountDevice(boot_partition)

  def _mountBootInBootPartition(self, mount_point):
    self._bootInBootMounted = False
    # assume that if the mount_point is /, any /boot directory is already accessible/mounted
    if mount_point != '/' and os.path.exists(os.path.join(mount_point, 'etc/fstab')):
      try:
        sltl.execCall("grep /boot {mp}/etc/fstab && chroot {mp} mount /boot".format(mp = mount_point))
        self._bootInBootMounted = True
      except:
        pass
    pass

  def _mountPartitions(self, partitions):
    """
    Return a list of mount points for each partition
    """
    mountPointList = []
    for p in partitions:
      mountPointList.append(sltl.mountDevice(p[0]))
    return mountPointList

  def _umountAll(self, mount_point, mountPointList):
    if self._bootInBootMounted:
      sltl.execCall("chroot {mp} umount /boot".format(mp = mount_point))
    for mp in mountPointList:
      sltl.umountDevice(mp)
    if mount_point != '/':
      sltl.umountDevice(mount_point)
    pass

  def _createLiloSections(self, partitions, mountPointList):
    """
    Return a list of lilo section string for each partition.
    There could be more section than partitions if there are multiple kernels.
    """
    sections = []
    for e in enumerate(partitions):
      i = e[0]
      p = e[1]
      mp = mountPointList[i]
      device = p[0]
      fs = p[1]
      bootType = p[2]
      label = p[3]
      if bootType == 'chain':
        sections.append(self._getChainLiloSection(device, label))
      elif bootType == 'linux':
        sections.extend(self._getLinuxLiloSections(device, fs, mp, label))
      else:
        sys.err.write("The boot type {type} is not supported.\n".format(type = bootType))
    return sections

  def _getChainLiloSection(self, device, label):
    """
    Returns a string for a chainloaded section
    """
    return """# {label} chain section
  other = {device}
  label = {label}
""".format(device = device, label = label)

  def _getLinuxLiloSections(self, device, fs, mp, label):
    """
    Returns a list of string sections, one for each kernel+initrd
    """
    sections = []
    kernelList = sorted(glob.glob("{mp}/boot/vmlinuz*".format(mp = mp)))
    initrdList = sorted(glob.glob("{mp}/boot/initr*".format(mp = mp)))
    uuid = sltl.execGetOutput(['/sbin/blkid', '-s', 'UUID', '-o', 'value', device], shell = False)
    for (k, i, l) in self._getKernelInitrdCouples(kernelList, initrdList, label):
      section = None
      if i:
        section = """# {l} Linux section
  image = {image}
  root = {root}
  initrd = {initrd}
""".format(image = k, initrd = i, root = "/dev/disk/by-uuid/{uuid}".format(uuid = uuid))
      else:
        section = """# {l} Linux section
  image = {image}
  root = {root}
""".format(image = k, root = "/dev/disk/by-uuid/{uuid}".format(uuid = uuid))
      if fs == 'ext4':
        section += '  append = "{append} "\n'.format(append = 'rootfstype=ext4')
      section += "  read-only\n  label = {label}\n".format(label = l)
      sections.append(section)
    return sections

  def _getKernelInitrdCouples(kernelList, initrdList, labelRef):
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
          ret.append(kernel, initrd, labelBase + str(n))
    return ret

  def _getFrameBufferConf(self):
    """
    Return the frame buffer configuration for this hardware.
    """
    fb_geometry = sltl.execGetOutput("fbset | grep -w geometry")
    mode = None
    if fb_geometry:
      vesa_modes = {
          '320x200x4' :None, '640x400x4' :None, '640x480x4' :None, '800x500x4' :None, '800x600x4' : 770, '896x672x4' :None, '1024x640x4' :None, '1024x768x4' : 772, '1152x720x4' :None, '1280x800x4:' :None, '1280x1024x4' : 774, '1400x1050x4' :None, '1440x900x4' :None, '1600x1200x4' :None, '1920x1200x4' :None,
          '320x200x8' :None, '640x400x8' : 768, '640x480x8' : 769, '800x500x8' : 879, '800x600x8' : 771, '896x672x8' : 815, '1024x640x8' : 874, '1024x768x8' : 773, '1152x720x8' : 869, '1280x800x8:' : 864, '1280x1024x8' : 775, '1400x1050x8' : 796, '1440x900x8' : 864, '1600x1200x8' : 796, '1920x1200x8' : 893,
          '320x200x15': 781, '640x400x15': 801, '640x480x15': 784, '800x500x15': 880, '800x600x15': 787, '896x672x15': 816, '1024x640x15': 875, '1024x768x15': 790, '1152x720x15': 870, '1280x800x15:': 865, '1280x1024x15': 793, '1400x1050x15': 797, '1440x900x15': 865, '1600x1200x15': 797, '1920x1200x15': 894,
          '320x200x16': 782, '640x400x16': 802, '640x480x16': 785, '800x500x16': 881, '800x600x16': 788, '896x672x16': 817, '1024x640x16': 876, '1024x768x16': 791, '1152x720x16': 871, '1280x800x16:': 866, '1280x1024x16': 794, '1400x1050x16': 798, '1440x900x16': 866, '1600x1200x16': 798, '1920x1200x16': 895,
          '320x200x24': 783, '640x400x24': 803, '640x480x24': 786, '800x500x24': 882, '800x600x24': 789, '896x672x24': 818, '1024x640x24': 877, '1024x768x24': 792, '1152x720x24': 872, '1280x800x24:': 867, '1280x1024x24': 795, '1400x1050x24': 799, '1440x900x24': 867, '1600x1200x24': 799, '1920x1200x24': 896,
          '320x200x32':None, '640x400x32': 804, '640x480x32': 809, '800x500x32': 883, '800x600x32': 814, '896x672x32': 819, '1024x640x32': 878, '1024x768x32': 824, '1152x720x32': 873, '1280x800x32:': 868, '1280x1024x32': 829, '1400x1050x32': 834, '1440x900x32': 868, '1600x1200x32': 834, '1920x1200x32': 897,
          }
      values = fb_geometry[0].split(' ')
      xres = values[1]
      yres = values[2]
      deep = values[-1]
      graphic_mode = "{x}x{y}x{d}".format(x = xres, y = yres, d = deep)
      if graphic_mode in vesa_modes:
        mode = vesa_modes[graphic_mode]
    if not mode:
      mode = 'normal'
    return mode

  def createConfiguration(self, mbr_device, boot_partition, partitions):
    """
    partitions format: [device, filesystem, boot type, label]
    """
    self.mbr_device = mbr_device
    self.boot_partition = boot_partition
    self.partitions = partitions
    try:
      mp = self._mountBootPartition(boot_partition)
      self._mountBootInBootPartition(mp)
      mpList = self._mountPartitions(partitions)
      liloSections = self._createLiloSections(partitions, mpList)
      fb = self._getFrameBufferConf()
      f = open(self.getConfigurationPath(), "w")
      f.write("""# LILO configuration file
# Generated by BootSetup
#
# Start LILO global section
# Append any additional kernel parameters:
append = "vt.default_utf8=1 "
boot = "{boot}"
lba32
compact

# Boot BMP Image.
# Bitmap in BMP format: 640x480x8
bitmap = /boot/salix.bmp
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
""".format( \
    boot = "/dev/" + mbr_device, \
    vga = fb \
    ))
      for s in liloSections:
        f.write(s)
        f.write("\n")
      f.close()
    finally:
      self._umountAll()

  def install(self):
    """
    Assuming that last configuration editing didn't modified mount point.
    """
    print "TODO install LiLo"
    mp = None
    try:
      mp = self._mountBootPartition(self.boot_partition)
      self._mountBootInBootPartition(mp)
      if mp != "/":
        # bind /dev and /proc in boot_partition
        sltl.execCall('mount -o bind /dev {mp}/dev'.format(mp = mp))
        sltl.execCall('mount -o bind /proc {mp}/proc'.format(mp = mp))
      mpList = self._mountPartitions(self.partitions)
      # copy the configuration to the boot_partition
      try:
        os.makedirs(os.path.join(mp, 'etc/bootsetup'))
      except os.error:
        pass
      shutil.copyfile(self.getConfigurationPath, os.path.join(mp, '/etc/bootsetup/lilo.conf'))
      # run lilo
      sltl.execCall('lilo -C {mp}/etc/bootsetup/lilo.conf'.format(mp = mp))
    finally:
      if mp and mp != "/":
        sltl.execCall('umount {mp}/proc'.format(mp = mp))
        sltl.execCall('umount {mp}/dev'.format(mp = mp))
      self._umountAll()
