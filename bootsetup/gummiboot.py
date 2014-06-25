#!/usr/bin/env python
# coding: utf-8
# vim:et:sta:sts=2:sw=2:ts=2:tw=0:
"""
GummiBoot bootloader.
"""
from __future__ import unicode_literals, print_function, division, absolute_import

from .efiboot import EFIBoot


class GummiBoot(EFIBoot):

  def __init__(self, isTest, secure_boot):
    super(self.__class__, self).__init__(isTest, secure_boot)
