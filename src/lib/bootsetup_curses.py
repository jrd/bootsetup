#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
Curses BootSetup.
"""
from __future__ import unicode_literals, print_function, division, absolute_import

__copyright__ = 'Copyright 2013-2014, Salix OS'
__license__ = 'GPL2+'

import os
import sys
import gettext  # noqa
import urwidm
from gathercurses import *
from bootsetup import *

class BootSetupCurses(BootSetup):
  
  gc = None
  _palette = [
      ('important', 'yellow', 'black', 'bold'),
      ('info', 'white', 'dark blue', 'bold'),
      ('error', 'white', 'dark red', 'bold'),
    ]

  def run_setup(self):
    urwidm.set_encoding('utf8')
    if os.getuid() != 0:
      self.error_dialog(_("Root privileges are required to run this program."), _("Sorry!"))
      sys.exit(1)
    self.gc = GatherCurses(self, self._version, self._bootloader, self._targetPartition, self._isTest, self._useTestData)
    self.gc.run()

  def _show_ui_dialog(self, dialog, parent = None):
    if not parent:
      parent = urwidm.Filler(urwidm.Divider(), 'top')
    uiToStop = False
    if self.gc and self.gc._loop:
      ui = self.gc._loop.screen
    else:
      ui = urwidm.raw_display.Screen()
      ui.register_palette(self._palette)
    if not ui._started:
      uiToStop = True
      ui.start()
    dialog.run(ui, parent)
    if uiToStop:
      ui.stop()

  def info_dialog(self, message, title = None, parent = None):
    if not title:
      title = _("INFO")
    dialog = urwidm.TextDialog(('info', unicode(message)), 10, 60, ('important', unicode(title)))
    self._show_ui_dialog(dialog, parent)

  def error_dialog(self, message, title = None, parent = None):
    if not title:
      title = "/!\ " + _("ERROR")
    dialog = urwidm.TextDialog(('error', unicode(message)), 10, 60, ('important', unicode(title)))
    self._show_ui_dialog(dialog, parent)
