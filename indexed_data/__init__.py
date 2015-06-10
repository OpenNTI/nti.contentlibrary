#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Indexed data is associated with content units and is typically
extracted at content rendering time.

It is typically accessed by adapting content units to the interfaces
of this package.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component

from .interfaces import TAG_NAMESPACE_FILE
from .interfaces import IContainedObjectCatalog

from zope.annotation.interfaces import IAnnotations

CATALOG_INDEX_NAME = '++etc++contentlibrary.container_index'

_KEY =  'nti.contentlibrary.indexed_data.LastModified'

def get_catalog():
	result = component.queryUtility( IContainedObjectCatalog, name=CATALOG_INDEX_NAME )
	return result
get_index = get_catalog

def _get_key( index_iface ):
	key = _KEY
	namespace = index_iface.queryTaggedValue( TAG_NAMESPACE_FILE,'' )
	if namespace:
		key = key + '_' + namespace
	return key

def get_index_last_modified( index_iface, unit ):
	key = _get_key( index_iface )
	annotes = IAnnotations( unit )
	return annotes.get( key )

def set_index_last_modified( index_iface, unit, now=None ):
	now = time.time() if now is None else now
	key = _get_key( index_iface )
	annotes = IAnnotations( unit )
	annotes[key] = now
