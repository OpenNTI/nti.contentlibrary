#!/usr/bin/env python
"""
Generic implementations of IContentUnit functions
"""
from __future__ import print_function, unicode_literals
logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.utils.property import alias
from nti.contentlibrary.interfaces import IContentUnit, IContentPackage


@interface.implementer(IContentUnit)
class ContentUnit(object):
	"""
	Simple implementation of :class:`IContentUnit`.
	"""

	_external_class_name_ = 'ContentUnit'

	ordinal = 1
	href = None
	ntiid = None
	icon = None

	# DCDescriptiveProperties
	title = None
	description = None


	children = ()
	__parent__ = None

	def __init__( self, **kwargs ):
		for k, v in kwargs.items():
			if hasattr( self, k ):
				setattr( self, k, v )

	__name__ = alias( 'title' )
	label = alias( 'title' )


	def __repr__( self ):
		return "<%s.%s '%s' '%s'>" % (self.__class__.__module__, self.__class__.__name__,
									  self.__name__, self.href )


@interface.implementer(IContentPackage)
class ContentPackage(ContentUnit):
	"""
	Simple implementation of :class:`IContentPackage`.
	"""

	_external_class_name_ = 'ContentPackage'

	root = None
	index = None
	index_last_modified = None
	installable = False
	archive = None
	archive_unit = None
	renderVersion = 1

	# IDCExtended
	creators = ()
	subjects = ()
	contributors = ()
	publisher = ''
