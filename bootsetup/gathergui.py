#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
Graphical BootSetup configuration gathering.
"""
from __future__ import unicode_literals, print_function, division, absolute_import

from .__init__ import __version__, __copyright__, __author__

import gettext  # noqa
import gobject
import gtk
import gtk.glade
import os
import sys
import re
import libsalt as slt
from .config import Config
from .lilo import Lilo
from .grub2 import Grub2
from .elilo import ELilo
from .gummiboot import GummiBoot


class GatherGui(object):
  """
  GUI to gather information about the configuration to setup.
  """

  _bootloader = None  # current bootloader instance
  _editing = False  # True when editing a boot label
  _custom_config = False  # True when a custom config (lilo.conf, elilo.conf, gummiboot entries) is being or has been edited

  def __init__(self, bootsetup, is_test=False, use_test_data=False, target_partition=None):
    self._bootsetup = bootsetup
    self.cfg = Config(is_test, use_test_data, target_partition)
    builder = gtk.Builder()
    if os.path.exists('bootsetup.glade'):
      builder.add_from_file('bootsetup.glade')
    else:
      raise Exception("bootsetup.glade not found")
    # Get a handle on the glade file widgets we want to interact with
    self.aboutDialog = builder.get_object("about_dialog")
    self.aboutDialog.set_version(__version__)
    self.aboutDialog.set_copyright(__copyright__)
    self.aboutDialog.set_authors(__author__)
    # Wizard window
    self.wizard = builder.get_object("bootsetup_page")
    self.contextualHelp = builder.get_object("help_context")
    # Different pages
    self.wizardPages = {}
    self.wizardPages['BootMode'] = builder.get_object("bootmode")
    self.wizardPages['BiosPartitions'] = builder.get_object("bios_partitions")
    self.wizardPages['BiosBootloaders'] = builder.get_object("bios_bootloaders")
    self.wizardPages['BootConfig'] = builder.get_object("boot_config")
    self.wizardPages['BiosGrub2'] = builder.get_object("bios_grub2")
    self.wizardPages['EFIPartitions'] = builder.get_object("efi_partitions")
    self.wizardPages['EFIBootloaders'] = builder.get_object("efi_bootloaders")
    self.wizardPages['EFIGrub2'] = builder.get_object("efi_grub2")
    self.wizardPages['Summary'] = builder.get_object("install_summary")
    # boot mode
    self.radioBios = builder.get_object("radiobutton_bios")
    self.radioEfi = builder.get_object("radiobutton_efi")
    self.checkSecureBoot = builder.get_object("checkbutton_secureboot")
    # bios partitions
    self.comboBoxMbr = builder.get_object("combobox_mbr")
    self._add_combobox_cell_renderer(self.comboBoxMbr, 1)
    self.comboBoxMbrEntry = self.comboBoxMbr.get_internal_child(builder, "entry")
    self.comboBoxBiosRootPartition = builder.get_object("combobox_bios_root_partition")
    self._add_combobox_cell_renderer(self.comboBoxBiosRootPartition, 2)
    self._add_combobox_cell_renderer(self.comboBoxBiosRootPartition, 1, padding=20)
    self.comboBoxBiosRootPartitionEntry = self.comboBoxBiosRootPartition.get_internal_child(builder, "entry")
    # bios boot loaders
    self.radioLilo = builder.get_object("radiobutton_lilo")
    self.radioGrub2 = builder.get_object("radiobutton_grub2")
    # bios lilo / boot config
    self.bootPartitionTreeview = builder.get_object("boot_partition_treeview")
    self.partitionTreeViewColumn = builder.get_object("partition_treeviewcolumn")
    self.fileSystemTreeViewColumn = builder.get_object("filesystem_treeviewcolumn")
    self.osTreeViewColumn = builder.get_object("os_treeviewcolumn")
    self.labelTreeViewColumn = builder.get_object("label_treeviewcolumn")
    self.labelCellRendererCombo = builder.get_object("label_cellrenderercombo")
    self.upButton = builder.get_object("up_button")
    self.downButton = builder.get_object("down_button")
    self.customUndoButton = builder.get_object("custom_undo_button")
    self.customEditButton = builder.get_object("custom_edit_button")
    # bios grub2
    self.comboBoxPartition = builder.get_object("combobox_partition")
    self._add_combobox_cell_renderer(self.comboBoxPartition, 2)
    self._add_combobox_cell_renderer(self.comboBoxPartition, 1, padding=20)
    self.comboBoxPartitionEntry = self.comboBoxPartition.get_internal_child(builder, "entry")
    self.grub2BiosEditButton = builder.get_object("grub2_bios_edit_button")
    # efi partitions
    self.comboBoxESP = builder.get_object("combobox_esp")
    self._add_combobox_cell_renderer(self.comboBoxESP, 2)
    self._add_combobox_cell_renderer(self.comboBoxESP, 1, padding=20)
    self.comboBoxESPEntry = self.comboBoxESP.get_internal_child(builder, "entry")
    self.comboBoxEfiRootPartition = builder.get_object("combobox_efi_root_partition")
    self._add_combobox_cell_renderer(self.comboBoxEfiRootPartition, 2)
    self._add_combobox_cell_renderer(self.comboBoxEfiRootPartition, 1, padding=20)
    self.comboBoxEfiRootPartitionEntry = self.comboBoxEfiRootPartition.get_internal_child(builder, "entry")
    # efi boot loaders
    self.radioGrub2Efi = builder.get_object("radiobutton_grub2_efi")
    self.radioELilo = builder.get_object("radiobutton_elilo")
    self.radioGummiBoot = builder.get_object("radiobutton_gummiboot")
    # efi grub2
    self.grub2EfiEditButton = builder.get_object("grub2_efi_edit_button")
    # summary
    self.installSummary = builder.get_object("install_summary")
    # other widgets
    self.quitButton = builder.get_object("button_quit")
    self.previousButton = builder.get_object("button_previous")
    self.nextButton = builder.get_object("button_next")
    self.installButton = builder.get_object("button_install")
    # list store
    self.diskListStore = builder.get_object("boot_disk_list_store")
    self.partitionListStore = builder.get_object("boot_partition_list_store")
    self.bootPartitionListStore = builder.get_object("boot_bootpartition_list_store")
    self.espPartitionListStore = builder.get_object("boot_esp_list_store")
    self.bootLabelListStore = builder.get_object("boot_label_list_store")
    # Initialize the contextual help box
    self.context_intro = _("<b>BootSetup will install a new bootloader on your computer.</b> \n\
\n\
A bootloader is required to load the main operating system of a computer and will initially display \
a boot menu if several operating systems are available on the same computer.")
    self.on_leave_notify_event(None)
    # Initialize the navigation wizard
    self.navigation = {
        'BootMode': (None, lambda: 'BiosPartitions' if self.cfg.cur_bootmode == 'bios' else 'EFIPartitions'),
        'BiosPartitions': ('BootMode', 'BiosBootloaders'),
        'BiosBootloaders': ('BiosPartitions', lambda: 'BootConfig' if self.cfg.cur_bootloader == 'lilo' else 'BiosGrub2'),
        'BootConfig': (lambda: 'BiosBootloaders' if self.cfg.cur_bootloader == 'lilo' else 'EFIBootloaders', 'Summary'),
        'BiosGrub2': ('BiosPartitions', 'Summary'),
        'EFIPartitions': ('BootMode', 'EFIBootloaders'),
        'EFIBootloaders': ('EFIPartitions', lambda: 'EFIGrub2' if self.cfg.cur_bootloader == 'grub2_efi' else 'BootConfig'),
        'EFIGrub2': ('EFIBootloaders', 'Summary'),
        'Summary': (lambda: 'EFIGrub2' if self.cfg.cur_bootloader == 'grub2_efi' else 'BootConfig', None)
    }
    self.wizard_page = None
    self.wizard_go()
    # Build data stores for filling combo boxes and grid tables
    self.build_data_stores()
    # Connect signals
    builder.connect_signals(self)

  def run(self):
    # indicates to gtk (and gdk) that we will use threads
    gtk.gdk.threads_init()
    # start the main gtk loop
    gtk.main()

  def _printCfg(self):
    if self.cfg and self.cfg.is_test:
      print(self.cfg)

  def _add_combobox_cell_renderer(self, comboBox, modelPosition, start=False, expand=False, padding=0):
    cell = gtk.CellRendererText()
    cell.set_property('xalign', 0)
    cell.set_property('xpad', padding)
    if start:
      comboBox.pack_start(cell, expand)
    else:
      comboBox.pack_end(cell, expand)
    comboBox.add_attribute(cell, 'text', modelPosition)

  def _set_text_for(self, widget, text):
    if text:
      widget.set_text(text)
    else:
      widget.set_text('')

  def build_data_stores(self):
    print('Building choice lists…', end='')
    sys.stdout.flush()
    self.diskListStore.clear()
    self.partitionListStore.clear()
    self.bootPartitionListStore.clear()
    self.espPartitionListStore.clear()
    for d in self.cfg.disks:
      self.diskListStore.append([d[0], d[2]])
    for p in self.cfg.partitions:  # for grub2 bios
      self.partitionListStore.append(p)
    for p in self.cfg.boot_partitions:  # for lilo, elilo, gummiboot
      p2 = list(p)  # copy p
      del p2[2]  # discard boot type
      p2[3] = re.sub(r'[()]', '', re.sub(r'_\(loader\)', '', re.sub(' ', '_', p2[3])))  # bootloader usually does not like spaces in labels
      p2.append('gtk-edit')  # add a visual
      self.bootPartitionListStore.append(p2)
    for p in self.cfg.esp:  # for EFI
      self.espPartitionListStore.append(p)
    self.labelCellRendererCombo.set_property("model", self.bootLabelListStore)
    self.labelCellRendererCombo.set_property('text-column', 0)
    self.labelCellRendererCombo.set_property('editable', True)
    self.labelCellRendererCombo.set_property('cell_background', '#CCCCCC')
    print(' Done')
    sys.stdout.flush()

  # What to do when BootSetup logo is clicked
  def on_about_button_clicked(self, widget, data=None):
    self.aboutDialog.show()

  # What to do when the about dialog quit button is clicked
  def on_about_dialog_close(self, widget, data=None):
    self.aboutDialog.hide()
    return True

  # What to do when the exit [X] on the main window upper right is clicked
  def gtk_main_quit(self, widget, data=None):
    if self._bootloader:
      del self._bootloader
    print("Bye _o/")
    gtk.main_quit()

  def process_gui_events(self):
    """
    be sure to treat any pending GUI events before continue
    """
    while gtk.events_pending():
      gtk.main_iteration()

  def update_gui_async(self, fct, *args, **kwargs):
    gobject.idle_add(fct, *args, **kwargs)

  def on_button_quit_clicked(self, widget, data=None):
    self.gtk_main_quit(widget)

  def get_previous_wizard_page(self, pageName):
    prevPage = self.navigation[pageName][0]
    if hasattr(prevPage, '__call__'):
      prevPage = prevPage()
    return prevPage

  def get_next_wizard_page(self, pageName):
    if pageName:
      nextPage = self.navigation[pageName][1]
    else:  # the first page is one that does not have previous page
      for page, info in self.navigation.iteritems():
        (prevPage, _) = info
        if prevPage is None:
          nextPage = page
          break
    if hasattr(nextPage, '__call__'):
      nextPage = nextPage()
    return nextPage

  def wizard_go(self, direction='next'):
    if direction not in ('previous', 'next'):
      raise Exception('direction should be previous or next')
    if direction == 'previous':
      page = self.get_previous_wizard_page(self.wizard_page)
    else:
      page = self.get_next_wizard_page(self.wizard_page)
    for p in self.wizardPages:
      if p == page:
        self.wizardPages[p].show()
      else:
        self.wizardPages[p].hide()
    prevPage = self.get_previous_wizard_page(page)
    if prevPage:
      self.quitButton.hide()
      self.previousButton.show()
    else:
      self.quitButton.show()
      self.previousButton.hide()
    nextPage = self.get_next_wizard_page(page)
    if nextPage:
      self.nextButton.show()
      self.installButton.hide()
    else:
      self.nextButton.hide()
      self.installButton.show()
    self.wizard_page = page
    self.wizard_prepare_page()
    self.wizard_update_buttons()

  def on_button_previous_clicked(self, widget):
    self.wizard_go('previous')

  def on_button_next_clicked(self, widget):
    self.wizard_go('next')

  def wizard_prepare_page(self):
    self._printCfg()
    if self.wizard_page == 'BootMode':
      self.radioEfi.set_sensitive(self.cfg.efi_firmware)
      self.checkSecureBoot.set_active(int(self.cfg.secure_boot))
      if self.cfg.cur_bootmode is None or self.cfg.cur_bootmode == 'bios':
        widget = self.radioBios
      else:
        widget = self.radioEfi
      widget.set_active(True)
      self.on_bootmode_clicked(widget)
      self.cfg.cur_bootloader = None
    elif self.wizard_page == 'BiosPartitions':
      self._set_text_for(self.comboBoxMbrEntry, self.cfg.cur_mbr_device)
      self._set_text_for(self.comboBoxBiosRootPartitionEntry, self.cfg.cur_root_partition)
    elif self.wizard_page == 'BiosBootloaders':
      self.radioGrub2.set_sensitive(Grub2.is_grub2_available(self.cfg.cur_root_partition))
      if self.cfg.cur_bootloader is None or self.cfg.cur_bootloader == 'lilo':
        widget = self.radioLilo
      else:
        widget = self.radioGrub2
      widget.set_active(True)
      self.on_bootloader_bios_clicked(widget)
    elif self.wizard_page == 'BootConfig':
      pass  # nothing to setup here.
    elif self.wizard_page == 'BiosGrub2':
      self._set_text_for(self.comboBoxPartitionEntry, self.cfg.cur_root_partition)
      self.update_grub2_bios_buttons()
    elif self.wizard_page == 'EFIPartitions':
      self._set_text_for(self.comboBoxESPEntry, self.cfg.cur_esp)
      self._set_text_for(self.comboBoxEfiRootPartitionEntry, self.cfg.cur_root_partition)
    elif self.wizard_page == 'EFIBootloaders':
      grub2_avail = Grub2.is_grub2_available(self.cfg.cur_root_partition)
      self.radioGrub2Efi.set_sensitive(grub2_avail)
      if self.cfg.cur_bootloader == 'grub2_efi' or (grub2_avail and self.cfg.cur_bootloader is None):
        widget = self.radioGrub2Efi
      elif self.cfg.cur_bootloader == 'elilo' or (not grub2_avail and self.cfg.cur_bootloader is None):
        widget = self.radioELilo
      else:
        widget = self.radioGummiBoot
      widget.set_active(True)
      self.on_bootloader_efi_clicked(widget)
    elif self.wizard_page == 'EFIGrub2':
      pass
    elif self.wizard_page == 'Summary':
      self.installSummary.set_text('TODO')  # TODO

  def wizard_update_buttons(self):
    nextOk = self.wizard_validate_page()
    self.nextButton.set_sensitive(nextOk)
    self.installButton.set_sensitive(nextOk)

  def wizard_validate_page(self):
    if self._editing:
      return False
    if self.wizard_page in ('BootMode', 'BiosBootloaders', 'EFIBootloaders', 'EFIGrub2'):
      return True
    elif self.wizard_page == 'BiosPartitions':
      mbr_ok = bool(self.cfg.cur_mbr_device) and os.path.exists(os.path.join(os.path.sep, 'dev', self.cfg.cur_mbr_device)) and bool(slt.getDiskInfo(self.cfg.cur_mbr_device))
      root_ok = bool(self.cfg.cur_root_partition) and os.path.exists(os.path.join(os.path.sep, 'dev', self.cfg.cur_root_partition)) and bool(slt.getPartitionInfo(self.cfg.cur_root_partition))
      return mbr_ok and root_ok
    elif self.wizard_page == 'BootConfig':
      return self.customEditButton.get_sensitive()
    elif self.wizard_page == 'BiosGrub2':
      return bool(self.cfg.cur_root_partition) and os.path.exists(os.path.join(os.path.sep, 'dev', self.cfg.cur_root_partition)) and bool(slt.getPartitionInfo(self.cfg.cur_root_partition))
    elif self.wizard_page == 'EFIPartitions':
      esp_ok = bool(self.cfg.cur_esp) and os.path.exists(os.path.join(os.path.sep, 'dev', self.cfg.cur_esp)) and self.cfg.cur_esp in [p[0] for p in self.cfg.esp]
      root_ok = bool(self.cfg.cur_root_partition) and os.path.exists(os.path.join(os.path.sep, 'dev', self.cfg.cur_root_partition)) and bool(slt.getPartitionInfo(self.cfg.cur_root_partition))
      return esp_ok and root_ok
    elif self.wizard_page == 'Summary':
      return False  # TODO

  def on_bootmode_clicked(self, widget, data=None):
    if widget.get_active():
      if widget == self.radioBios:
        self.cfg.cur_bootmode = 'bios'
        self.checkSecureBoot.hide()
      else:
        self.cfg.cur_bootmode = 'efi'
        self.checkSecureBoot.show()
    self.wizard_update_buttons()

  def on_checkbutton_secureboot_toggled(self, widget, data=None):
    self.cfg.secure_boot = bool(widget.get_active())
    self.wizard_update_buttons()

  def on_combobox_mbr_changed(self, widget, data=None):
    self.cfg.cur_mbr_device = self.comboBoxMbrEntry.get_text()
    self.wizard_update_buttons()

  def on_combobox_bios_root_partition_changed(self, widget, data=None):
    self.cfg.cur_root_partition = self.comboBoxBiosRootPartitionEntry.get_text()
    self.wizard_update_buttons()

  def on_bootloader_bios_clicked(self, widget, data=None):
    if widget.get_active():
      if widget == self.radioLilo:
        self.cfg.cur_bootloader = 'lilo'
        self._bootloader = Lilo(self.cfg.is_test)
      else:
        self.cfg.cur_bootloader = 'grub2'
        self._bootloader = Grub2(self.cfg.is_test)
    self.wizard_update_buttons()

  def set_editing_mode(self, is_edit):
    self._editing = is_edit
    self.update_grid_buttons()

  def on_label_cellrenderercombo_editing_started(self, widget, path, data):
    self.set_editing_mode(True)

  def on_label_cellrenderercombo_editing_canceled(self, widget):
    self.set_editing_mode(False)

  def on_label_cellrenderercombo_edited(self, widget, row_number, new_text):
    row_number = int(row_number)
    max_chars = 15
    if ' ' in new_text:
      self._bootsetup.error_dialog(_("\nAn Operating System label should not contain spaces.\n\nPlease check and correct.\n"))
    elif len(new_text) > max_chars:
      self._bootsetup.error_dialog(_("\nAn Operating System label should not be more than {max} characters long.\n\nPlease check and correct.\n".format(max=max_chars)))
    else:
      model, it = self.bootPartitionTreeview.get_selection().get_selected()
      found = False
      for i, line in enumerate(model):
        if i == row_number or line[3] == _("Set..."):
          continue
        if line[3] == new_text:
          found = True
          break
      if found:
        self._bootsetup.error_dialog(_("You have used the same label for different Operating Systems. Please check and correct.\n"))
      else:
        model.set_value(it, 3, new_text)
        if new_text == _("Set..."):
          model.set_value(it, 4, "gtk-edit")
        else:
          model.set_value(it, 4, "gtk-yes")
    self.set_editing_mode(False)

  def on_up_button_clicked(self, widget, data=None):
    """
    Move the row items upward.

    """
    # Obtain selection
    sel = self.bootPartitionTreeview.get_selection()
    # Get selected path
    (model, rows) = sel.get_selected_rows()
    if not rows:
      return
    # Get new path for each selected row and swap items.
    for path1 in rows:
      # Move path2 upward
      path2 = (path1[0] - 1,)
    # If path2 is negative, the user tried to move first path up.
    if path2[0] < 0:
      return
    # Obtain iters and swap items.
    iter1 = model.get_iter(path1)
    iter2 = model.get_iter(path2)
    model.swap(iter1, iter2)

  def on_down_button_clicked(self, widget, data=None):
    """
    Move the row items downward.

    """
    # Obtain selection
    sel = self.bootPartitionTreeview.get_selection()
    # Get selected path
    (model, rows) = sel.get_selected_rows()
    if not rows:
      return
    # Get new path for each selected row and swap items.
    for path1 in rows:
      # Move path2 downward
      path2 = (path1[0] + 1,)
    # If path2 is negative, we're trying to move first path up.
    if path2[0] < 0:
      return
    # Obtain iters and swap items.
    iter1 = model.get_iter(path1)
    # If the second iter is invalid, the user tried to move the last item down.
    try:
      iter2 = model.get_iter(path2)
    except ValueError:
      return
    model.swap(iter1, iter2)

  def _create_boot_config(self):
    partitions = []
    for row in self.bootPartitionListStore:
      p = list(row)
      if p[4] == "gtk-yes":
        dev = p[0]
        fs = p[1]
        t = "chain"
        for p2 in self.cfg.boot_partitions:
          if p2[0] == dev:
            t = p2[2]
            break
        label = p[3]
        partitions.append([dev, fs, t, label])
    self._bootloader.createConfiguration(self.cfg.cur_mbr_device, self.cfg.cur_esp, self.cfg.cur_root_partition, partitions)

  def _edit_file(self, filename):
    launched = False
    for editor in ('leafpad', 'gedit', 'geany', 'kate', 'xterm -e nano'):
      try:
        cmd = editor.split(' ').append(filename)
        slt.execCall(cmd, shell=True, env=None)
        launched = True
        break
      except:
        pass
    return launched

  def on_custom_edit_button_clicked(self, widget, data=None):
    custom_cfg = self._bootloader.getConfigurationPath()
    if not os.path.exists(custom_cfg):
      self._custom_config = True
      self.update_grid_buttons()
      self._create_boot_config()
    if os.path.exists(custom_cfg):
      if not self._edit_file(custom_cfg):
        self._custom_config = False
        self.update_grid_buttons()
        self._bootsetup.error_dialog(_("Sorry, BootSetup is unable to find a suitable text editor in your system. You will not be able to manually modify the {bootloader} configuration.\n").format(bootloader=self.cfg.cur_bootloader))

  def on_custom_undo_button_clicked(self, widget, data=None):
    custom_cfg = self._bootloader.getConfigurationPath()
    if os.path.exists(custom_cfg):
      os.remove(custom_cfg)
    self._custom_config = False
    self.update_grid_buttons()

  def update_grid_buttons(self):
    multiple = len(self.bootPartitionListStore) > 1
    labels_ok = True
    for bp in self.bootPartitionListStore:
      if bp[4] != "gtk-yes":
        labels_ok = False
        break
    self.bootPartitionTreeview.set_sensitive(not self._custom_config)
    self.upButton.set_sensitive(not self._editing and multiple)
    self.downButton.set_sensitive(not self._editing and multiple)
    self.customUndoButton.set_sensitive(not self._editing and self._custom_config)
    self.customEditButton.set_sensitive(not self._editing and labels_ok)
    self.wizard_update_buttons()

  def on_combobox_partition_changed(self, widget, data=None):
    self.cfg.cur_root_partition = self.comboBoxPartitionEntry.get_text()
    self.update_grub2_bios_buttons()

  def on_grub2_bios_edit_button_clicked(self, widget, data=None):
    partition = os.path.join(os.path.sep, 'dev', self.cfg.cur_root_partition)
    if slt.isMounted(partition):
      mp = slt.getMountPoint(partition)
      doumount = False
    else:
      mp = slt.mountDevice(partition)
      doumount = True
    grub2cfg = os.path.join(mp, 'etc', 'default', 'grub')
    try:
      if os.path.exists(grub2cfg):
        if not self._edit_file(grub2cfg):
          self._bootsetup.error_dialog(_("Sorry, BootSetup is unable to find a suitable text editor in your system. You will not be able to manually modify the {bootloader} configuration.\n").format(bootloader='Grub2'))
      else:
        self._bootsetup.error_dialog(_("Sorry, etc/default/grub seems to be missing in {device}.\n").format(device=self.cfg.cur_root_partition))
    finally:  # be sure to go here even if an unexpected exception occured
      if doumount:
        slt.umountDevice(mp)

  def update_grub2_bios_buttons(self):
    self.grub2BiosEditButton.set_sensitive(os.path.exists(os.path.join(os.path.sep, 'dev', self.cfg.cur_root_partition)))
    self.wizard_update_buttons()

  def on_combobox_esp_changed(self, widget, data=None):
    self.cfg.cur_esp = self.comboBoxESPEntry.get_text()
    self.wizard_update_buttons()

  def on_combobox_efi_root_partition_changed(self, widget, data=None):
    self.cfg.cur_root_partition = self.comboBoxEfiRootPartitionEntry.get_text()
    self.wizard_update_buttons()

  def on_bootloader_efi_clicked(self, widget, data=None):
    if widget.get_active():
      if widget == self.radioGrub2Efi:
        self.cfg.cur_bootloader = 'grub2_efi'
        self._bootloader = Grub2(self.cfg.is_test, self.cfg.secure_boot)
      elif widget == self.radioELilo:
        self.cfg.cur_bootloader = 'elilo'
        self._bootloader = ELilo(self.cfg.is_test, self.cfg.secure_boot)
      else:
        self.cfg.cur_bootloader = 'gummiboot'
        self._bootloader = GummiBoot(self.cfg.is_test, self.cfg.secure_boot)
    self.wizard_update_buttons()

  def on_grub2_efi_edit_button_clicked(self, widget, data=None):
    partition = os.path.join(os.path.sep, 'dev', self.cfg.cur_esp)
    if slt.isMounted(partition):
      mp = slt.getMountPoint(partition)
      doumount = False
    else:
      mp = slt.mountDevice(partition)
      doumount = True
    grub2cfg = os.path.join(mp, 'EFI', 'Boot', 'grub', 'grub.cfg')
    if os.path.exists(grub2cfg):
      if not self._edit_file(grub2cfg):
        self._bootsetup.error_dialog(_("Sorry, BootSetup is unable to find a suitable text editor in your system. You will not be able to manually modify the {bootloader} configuration.\n").format(bootloader='Grub2'))
    if doumount:
      slt.umountDevice(mp)

  def update_buttons(self):
    install_ok = False
    multiple = False
    grub2_edit_ok = False
    if self.cfg.cur_mbr_device and os.path.exists("/dev/{0}".format(self.cfg.cur_mbr_device)) and slt.getDiskInfo(self.cfg.cur_mbr_device):
      if self.cfg.cur_bootloader == 'lilo' and not self._editing:
        if len(self.BootPartitionListStore) > 1:
          multiple = True
        for bp in self.BootPartitionListStore:
          if bp[4] == "gtk-yes":
            install_ok = True
      elif self.cfg.cur_bootloader == 'grub2':
        if self.cfg.cur_root_partition and os.path.exists(os.path.sep, 'dev', self.cfg.cur_root_partition) and slt.getPartitionInfo(self.cfg.cur_root_partition):
          install_ok = True
        if install_ok:
          partition = os.path.join("/dev", self.cfg.cur_root_partition)
          if slt.isMounted(partition):
            mp = slt.getMountPoint(partition)
            doumount = False
          else:
            mp = slt.mountDevice(partition)
            doumount = True
          grub2_edit_ok = os.path.exists(os.path.join(mp, 'etc', 'default', 'grub'))
          if doumount:
            slt.umountDevice(mp)
    self.RadioLilo.set_sensitive(not self._editing)
    self.RadioGrub2.set_sensitive(not self._editing)
    self.ComboBoxMbr.set_sensitive(not self._editing)
    self.BootPartitionTreeview.set_sensitive(not self._custom_lilo)
    self.UpButton.set_sensitive(not self._editing and multiple)
    self.DownButton.set_sensitive(not self._editing and multiple)
    self.LiloUndoButton.set_sensitive(not self._editing and self._custom_lilo)
    self.LiloEditButton.set_sensitive(not self._editing and install_ok)
    self.Grub2BiosEditButton.set_sensitive(grub2_edit_ok)
    self.ExecuteButton.set_sensitive(not self._editing and install_ok)

  def on_execute_button_clicked(self, widget, data=None):
    if self.cfg.cur_bootloader == 'lilo':
      if not os.path.exists(self._lilo.getConfigurationPath()):
        self._create_boot_config()
      self._lilo.install()
    elif self.cfg.cur_bootloader == 'grub2':
      self._grub2.install(self.cfg.cur_mbr_device, self.cfg.cur_esp, self.cfg.cur_root_partition)
    elif self.cfg.cur_bootloader == 'elilo':
      self._elilo.install(self.cfg.cur_esp, self.cfg.cur_root_partition)
    elif self.cfg.cur_bootloader == 'gummiboot':
      self._gummiboot.install(self.cfg.cur_esp, self.cfg.cur_root_partition)
    self.installation_done()

  def installation_done(self):
    print("Bootloader Installation Done.")
    msg = "<b>{0}</b>".format(_("Bootloader installation process completed."))
    self._bootsetup.info_dialog(msg)
    self.gtk_main_quit(self.Window)

  # General contextual help
  def on_leave_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(self.context_intro)

  def on_about_button_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_text(_("About BootSetup."))

  def on_bootloader_bootmode_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("You need a bootloader to load an OS for you computer.\n\
Two boot modes exists to run a bootloader. EFI is the new one. Use this if possible."))

  def on_bootloader_type_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("Here you can choose between LiLo or the Grub2 bootloader.\n\
Both will boot your Linux and (if applicable) Windows.\n\
LiLo is the old way but still works pretty well. A good choice if you have a simple setup.\n\
Grub2 is a full-featured bootloader and more robust (does not rely on blocklists)."))

  def on_bootloader_typeefi_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("Here you can choose between ELiLo, Grub2 or the GummiBoot bootloader.\n\
ELiLo can only boot Linux. Grub2 can boot anything. GummiBoot can boot EFI applications/OS only.\n\
Use ELiLo only if you know you will using only one Linux OS and no Windows.\n\
Grub2 discover new installed OS automatically."))

  def on_combobox_mbr_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("Select the device that will contain your bootloader.\n\
This is commonly the device you set your Bios to boot on."))

  def on_boot_partition_treeview_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("Here you must define a boot menu label for each \
of the operating systems that will be displayed in your bootloader menu.\n\
Any partition for which you do not set a boot menu label will not be configured and will \
not be displayed in the bootloader menu.\n\
If several kernels are available within one partition, the label you have chosen for that \
partition will be appended numerically to create multiple menu entries for each of these kernels.\n\
Any of these settings can be edited manually in the configuration file."))

  def on_up_button_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("Use this arrow if you want to move the \
selected Operating System up to a higher rank.\n\
The partition with the highest rank will be displayed on the first line of the bootloader menu.\n\
Any of these settings can be edited manually in the configuration file."))

  def on_down_button_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("Use this arrow if you want to move the \
selected Operating System down to a lower rank.\n\
The partition with the lowest rank will be displayed on the last line of the bootloader menu.\n\
Any of these settings can be edited manually in the configuration file."))

  def on_lilo_undo_button_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("This will undo all settings (even manual modifications)."))

  def on_lilo_edit_button_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("Experienced users can \
manually edit the LiLo configuration file.\n\
Please do not tamper with this file unless you know what you are doing and you have \
read its commented instructions regarding chrooted paths."))

  def on_combobox_partition_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("Select the partition that will contain the Grub2 files.\n\
These will be in /boot/grub/. This partition should be readable by Grub2.\n\
It is recommanded to use your / partition, or your /boot partition if you have one."))

  def on_grub2_edit_button_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("You can edit the etc/default/grub file for \
adjusting the Grub2 settings.\n\
This will not let you choose the label or the order of the menu entries, \
it's automatically done by Grub2."))

  def on_button_quit_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_text(_("Exit BootSetup program."))

  def on_execute_button_enter_notify_event(self, widget, data=None):
    self.contextualHelp.set_markup(_("Once you have defined your settings, \
click on this button to install your bootloader."))
