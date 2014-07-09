#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Container implementations.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from .interfaces import IWritableIndexedDataContainer
from .interfaces import IAudioIndexedDataContainer
from .interfaces import IRelatedContentIndexedDataContainer
from .interfaces import IVideoIndexedDataContainer

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from zope.cachedescriptors.property import Lazy
from zc.dict import Dict

class _IndexedDataDict(Dict):
	__parent__ = None
	__name__ = None

@interface.implementer(IWritableIndexedDataContainer)
class IndexedDataContainer(PersistentCreatedAndModifiedTimeObject):

	__parent__ = None
	__name__ = None

	def __init__(self, ntiid):
		super(IndexedDataContainer,self).__init__()
		self.ntiid = ntiid
		# Override the super and do not set lastModified
		# to current time because we will want to track it
		# externally; instead, set it to the default for
		# "unknown"
		self.lastModified = -1

	@Lazy
	def _data(self):
		data = _IndexedDataDict()
		data.__parent__ = self
		self._p_changed = True
		return data

	def get_data_items(self):
		return self._data.values()

	def contains_data_item_with_ntiid(self, ntiid):
		self._p_activate()
		return '_data' in self.__dict__ and ntiid in self._data

	def set_data_items(self, data_items):
		self._p_activate()
		if '_data' in self.__dict__:
			self._data.clear()
		if not data_items:
			return

		data = self._data
		for item in data_items:
			data[item['ntiid']] = item

	def __len__(self):
		self._p_activate()
		if '_data' in self.__dict__:
			return len(self._data)
		return 0

@interface.implementer(IAudioIndexedDataContainer)
class AudioIndexedDataContainer(IndexedDataContainer):
	pass


@interface.implementer(IVideoIndexedDataContainer)
class VideoIndexedDataContainer(IndexedDataContainer):
	pass


@interface.implementer(IRelatedContentIndexedDataContainer)
class RelatedContentIndexedDataContainer(IndexedDataContainer):
	pass