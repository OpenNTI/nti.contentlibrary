#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of content bundles.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope import lifecycleevent
from zope.event import notify

from nti.utils.property import alias

from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createFieldProperties
from nti.schema.fieldproperty import createDirectFieldProperties
from nti.schema.schema import EqHash

from nti.externalization.externalization import WithRepr
from nti.externalization.persistence import NoPickle

import anyjson as json


# Because we only expect to store persistent versions
# of these things, and we expect to update them directly
# in place, we make them attribute annotatable.
from zope.annotation.interfaces import IAttributeAnnotatable

from .interfaces import IContentPackageBundle
from .interfaces import IContentPackageBundleLibrary
from .interfaces import IDisplayableContent

from nti.wref.interfaces import IWeakRef

from nti.dataserver.containers import CheckingLastModifiedBTreeContainer
from nti.dublincore.time_mixins import CreatedAndModifiedTimeMixin
from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from .presentationresource import DisplayableContentMixin

@interface.implementer(IContentPackageBundle,
					   IAttributeAnnotatable)
@WithRepr
class ContentPackageBundle(CreatedAndModifiedTimeMixin,
						   DisplayableContentMixin,
						   SchemaConfigured):

	"""
	Basic implementation of a content package bundle.
	"""
	__external_class_name__ = 'ContentPackageBundle'
	__external_can_create__ = False

	# Equality and hashcode not defined on purpose,
	# identity semantics for now!

	# Be careful not to overwrite what we inherit
	createFieldProperties(IDisplayableContent,
						  omit='PlatformPresentationResources')
	createDirectFieldProperties(IContentPackageBundle)

	# the above defined the ntiid property and the name
	# property, but the ntiid property has the constraint on it
	# that we need.
	__name__ = alias('ntiid')

	# IDCExtendedProperties.
	# Note that we're overriding these to provide
	# default values, thus losing the FieldProperty
	# implementation
	creators = ()
	subjects = ()
	contributors = ()
	publisher = ''

	@property
	def PlatformPresentationResources(self):
		"""
		If we do not have a set of presentation assets,
		we echo the first content package we have that does contain
		them. This should simplify things for the clients.
		"""
		ours = super(ContentPackageBundle,self).PlatformPresentationResources
		if ours:
			return ours

		for package in self.ContentPackages:
			theirs = package.PlatformPresentationResources
			if theirs:
				return theirs

		return ()

class PersistentContentPackageBundle(PersistentCreatedAndModifiedTimeObject,
									 ContentPackageBundle):
	"""
	A persistent implementation of content package bundles.

	As required, references to content packages are
	maintained weakly.
	"""

	_ContentPackages_wrefs = ()

	def _set_ContentPackages(self, packages):
		self._ContentPackages_wrefs = tuple([IWeakRef(p) for p in packages])
		if len(self._ContentPackages_wrefs) != len(set(self._ContentPackages_wrefs)):
			raise ValueError("Duplicate packages")
	def _get_ContentPackages(self):
		result = list()
		for x in self._ContentPackages_wrefs:
			x = x()
			if x is not None:
				result.append(x)
		return result
	ContentPackages = property(_get_ContentPackages, _set_ContentPackages)


_marker = object()

@interface.implementer(IContentPackageBundleLibrary)
class ContentPackageBundleLibrary(CheckingLastModifiedBTreeContainer):
	"""
	BTree-based implementation of a bundle library.
	"""
	__external_can_create__ = False

	def __repr__(self):
		return "<%s(%s, %s) at %s>" % (self.__class__.__name__, self.__name__, len(self), id(self))

	@property
	def _parent_lib(self):
		return component.queryNextUtility(self, IContentPackageBundleLibrary)

	# Only these methods are expected to walk up the utility tree

	def get(self, key, default=None):
		obj = CheckingLastModifiedBTreeContainer.get(self, key, _marker)
		if obj is _marker:
			obj = default
			parent_lib = self._parent_lib
			if parent_lib is not None:
				obj = parent_lib.get(key, default)

		return obj

	def __getitem__(self, key):
		try:
			return CheckingLastModifiedBTreeContainer.__getitem__(self, key)
		except KeyError:
			parent_lib = self._parent_lib
			if parent_lib is None:
				raise

			return parent_lib[key]

	def getBundles(self):
		# recall that lower bundles override higher ones
		seen_ids = set()
		for k, v in self.items():
			seen_ids.add(k)
			yield v

		parent_lib = self._parent_lib
		if parent_lib is None:
			# done
			return

		for bundle in parent_lib.getBundles():
			if bundle.__name__ in seen_ids:
				continue
			seen_ids.add(bundle.__name__)
			yield bundle

#: The name of the file that identifies a directory
#: as a content bundle
_BUNDLE_META_NAME = "bundle_meta_info.json"

from .interfaces import ISyncableContentPackageBundleLibrary
from .interfaces import IEnumerableDelimitedHierarchyBucket
from .interfaces import IDelimitedHierarchyKey
from .interfaces import IContentPackageLibrary
from .interfaces import ContentPackageBundleLibraryModifiedOnSyncEvent

from nti.schema.field import IndexedIterable
from nti.ntiids.schema import ValidNTIID
from nti.schema.schema import PermissiveSchemaConfigured

from .wref import contentunit_wref_to_missing_ntiid

class _IContentBundleMetaInfo(IContentPackageBundle):

	ContentPackages = IndexedIterable(title="An iterable of NTIIDs of sub-containers embedded via reference in this content",
									  value_type=ValidNTIID(title="The embedded NTIID"),
									  unique=True,
									  default=())

@interface.implementer(_IContentBundleMetaInfo)
@EqHash('ntiid')
@NoPickle
@WithRepr
class _ContentBundleMetaInfo(PermissiveSchemaConfigured):
	"""
	Meta-information
	"""

	createFieldProperties(_IContentBundleMetaInfo)

	def __init__(self, key, content_library):
		# For big/complex JSON, we want to avoid loading the JSON
		# and turning it indo objects unless the timestamp is newer;
		# however, here we need the NTIID, which comes out of the file;
		# also we expect it to be quite small
		json_text = key.readContents().decode('utf-8')
		self.json_value = json.loads(json_text)
		# TODO: If there is no NTIID, we should derive one automatically
		# from the key name
		if 'ntiid' not in self.json_value:
			raise ValueError("Missing ntiid", key)

		super(_ContentBundleMetaInfo, self).__init__(**self.json_value)
		self.lastModified = key.lastModified
		self.createdTime = key.createdTime
		self.key = key

		if self.ContentPackages:
			self.__dict__[str('ContentPackages')] = self.getContentPackagesWrefs(content_library)


	def getContentPackagesWrefs(self, library):
		"""
		persistent content bundles want to refer to weak refs;
		we read the meta as ntiid strings that we either resolve
		to actual packages, or weak refs to missing ntiids
		"""
		cps = []
		for ntiid in self.ContentPackages:
			cp = library.get(ntiid)
			if cp:
				cps.append(cp)
			else:
				cps.append(contentunit_wref_to_missing_ntiid(ntiid))

		return cps

def _readCurrent(lib):
	try:
		lib._p_jar.readCurrent(lib)
	except AttributeError:
		pass
	try:
		lib._SampleContainer__data._p_jar.readCurrent(lib._SampleContainer__data)
	except AttributeError:
		pass


@interface.implementer(ISyncableContentPackageBundleLibrary)
@component.adapter(IContentPackageBundleLibrary)
class _ContentPackageBundleLibrarySynchronizer(object):

	def __init__(self, context):
		self.context = context

	def syncFromBucket(self, bucket):

		content_library = component.getSiteManager(self.context).getUtility(IContentPackageLibrary)
		_readCurrent(content_library)
		_readCurrent(self.context)

		bundle_meta_keys = list()

		for child in bucket.enumerateChildren():
			if not IEnumerableDelimitedHierarchyBucket.providedBy(child):
				# not a directory
				continue
			bundle_meta_key = child.getChildNamed(_BUNDLE_META_NAME)
			if not IDelimitedHierarchyKey.providedBy(bundle_meta_key):
				# Not a readable file
				continue

			bundle_meta_keys.append(bundle_meta_key)

		need_event = False

		# Trivial case: everything is gone
		# TODO: How do we want to handle deletions?
		# Ideally we want to "archive" the objects somewhere probably
		# (a special 'archive' subcontainer?)

		if not bundle_meta_keys and self.context:
			logger.info("Removing all bundles from library %s: %s", self.context, list(self.context))
			need_event = True
			for k in list(self.context):
				del self.context[k] # fires bunches of events
		else:
			bundle_metas = {_ContentBundleMetaInfo(k, content_library) for k in bundle_meta_keys}
			all_ntiids = {x.ntiid for x in bundle_metas}
			# Now determine what to add/update/remove.
			# Order matters here, very much.
			# The __contains__ operation for keys does not take parent
			# libraries into account, nor does iterating the keys; thus,
			# we're safe by checking the ntiids against our context.
			# By the time we look for things to update, we know we will
			# be accessing an item local in our context, not from parent,
			# even though __getitem__ is recursive.

			things_to_add = {x for x in bundle_metas if x.ntiid not in self.context}
			# Take those out
			bundle_metas = bundle_metas - things_to_add

			things_to_update = {x for x in bundle_metas
								if x.lastModified > self.context[x.ntiid].lastModified}

			# All of these remaining things haven't changed,
			# but by definition must still be in the container
			bundle_metas = bundle_metas - things_to_update

			# any ntiids in the container that we don't have on disk
			# have to go
			del_ntiids = {x for x in self.context if x not in all_ntiids}

			def _update_bundle(bundle, meta):
				bundle_iface = interface.providedBy(bundle)
				# Be careful to only update fields that have changed
				for k in meta.__dict__:
					if bundle_iface.get(k) and getattr(bundle, k, None) != getattr(meta, k):
						setattr(bundle, str(k), getattr(meta, k))

				if bundle.root != meta.key.__parent__:
					bundle.root = meta.key.__parent__
				# by definition this has changed or we wouldn't be here
				bundle.lastModified = meta.lastModified

				assert meta.ntiid == bundle.ntiid


			# Start with the adds
			if things_to_add:
				need_event = True
				logger.info("Adding bundles to library %s: %s",
							self.context, things_to_add)
				for meta in things_to_add:
					bundle = PersistentContentPackageBundle()
					bundle.createdTime = meta.createdTime
					_update_bundle( bundle, meta )

					lifecycleevent.created(bundle)
					self.context[meta.ntiid] = bundle # added

			# Now the deletions
			if del_ntiids:
				logger.info("Removing bundles from library %s: %s",
							self.context, del_ntiids)
				for ntiid in del_ntiids:
					need_event = True
					del self.context[ntiid]

			# Now any updates
			if things_to_update:
				need_event = True
				logger.info("Updating bundles in library %s: %s",
							self.context, things_to_update)

				for meta in things_to_update:
					bundle = self.context[meta.ntiid]
					_update_bundle(bundle, meta)
					# TODO: make update_bundle return the changed attributes?
					lifecycleevent.modified(bundle)

		if need_event:
			event = ContentPackageBundleLibraryModifiedOnSyncEvent(self.context)
			event.bucket = bucket
			notify(event)
		else:
			logger.info("Nothing to do to sync library %s", self.context)
