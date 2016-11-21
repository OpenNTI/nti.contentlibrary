#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Deals with a lot of cross-version issues.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# Taken from https://github.com/gorakhargosh/mom

import sys
import types

PY3 = sys.version_info[0] == 3

if PY3:  # pragma: no cover
	string_types = str,
	integer_types = int,
	class_types = type,
	text_type = str
	binary_type = bytes
else:
	string_types = basestring,
	integer_types = (int, long)
	class_types = (type, types.ClassType)
	text_type = unicode
	binary_type = str
