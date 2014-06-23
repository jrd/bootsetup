#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
GummiBoot bootloader.
"""
from __future__ import unicode_literals, print_function, division, absolute_import

import codecs


class GummiBoot:
  isTest = False

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
