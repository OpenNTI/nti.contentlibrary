#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Objects for creating IContentLibrary objects based on the filesystem.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from persistent import Persistent

from zope import interface

from nti.base.interfaces import ILastModified

from nti.containers.containers import LastModifiedBTreeContainer

from nti.contentlibrary.bucket import AbstractKey
from nti.contentlibrary.bucket import AbstractBucket

from nti.contentlibrary.interfaces import IDelimitedHierarchyKey
from nti.contentlibrary.interfaces import IEnumerableDelimitedHierarchyBucket

from nti.coremetadata.interfaces import ITitledContent

from nti.dublincore.time_mixins import CreatedAndModifiedTimeMixin

from nti.property.property import alias

@interface.implementer(IDelimitedHierarchyKey,
					   ILastModified)
class PersistentHierarchyKey(AbstractKey,
							 Persistent,
							 CreatedAndModifiedTimeMixin,
							 ITitledContent):

	_contents = None
	data = alias('_contents')

	def __init__(self, contents, *args, **kwargs):
		super( PersistentHierarchyKey, self ).__init__(*args, **kwargs)
		self._contents = contents

	def readContents(self):
		return self._contents

@interface.implementer(IEnumerableDelimitedHierarchyBucket)
class PersistentHierarchyBucket(LastModifiedBTreeContainer, AbstractBucket):

	def enumerateChildren(self):
		return self.values()

