#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic key and bucket implementations.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from .interfaces import IDelimitedHierarchyBucket
from .interfaces import IDelimitedHierarchyKey

from nti.utils.property import alias

from nti.schema.schema import EqHash

@EqHash('bucket', 'name')
class _AbstractDelimitedHierarchyObject(object):

	__name__ = None
	__parent__ = None

	bucket = alias('__parent__')
	name = alias('__name__')

	# BWC we allow key
	key = alias('name')


	def __init__(self, bucket=None, name=None):
		# by convention, parent is the first argument.
		if bucket is not None:
			self.bucket = bucket
		if name is not None:
			self.name = name

	def __repr__(self):
		return "<%s '%s'/'%s'>" % (type(self).__name__, self.bucket, self.name.encode('unicode_escape'))


@interface.implementer(IDelimitedHierarchyBucket)
class AbstractBucket(_AbstractDelimitedHierarchyObject):
	pass

@interface.implementer(IDelimitedHierarchyKey)
class AbstractKey(_AbstractDelimitedHierarchyObject):
	"""
	To simplify programming, we provide an :meth:`enumerateChlidren`
	method that returns an empty list.
	"""

	def enumerateChildren(self):
		return ()
