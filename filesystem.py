#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Objects for creating IContentLibrary objects based on the filesystem.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
from os.path import join as path_join

from zope import interface
from zope.location.interfaces import IContained as IZContained

import repoze.lru

from nti.utils.property import alias, CachedProperty

from . import eclipse
from . import library

from .contentunit import ContentUnit
from .contentunit import ContentPackage
from .interfaces import IFilesystemContentUnit
from .interfaces import IFilesystemContentPackage
from .interfaces import IFilesystemContentPackageLibrary
from .interfaces import IFilesystemKey
from .interfaces import IFilesystemBucket

def _TOCPath(path):
	return os.path.abspath(path_join(path, eclipse.TOC_FILENAME))

def _hasTOC(path):
	""" Does the given path point to a directory containing a TOC file?"""
	return os.path.exists(_TOCPath(path))

def _isTOC(path):
	return os.path.basename(path) == eclipse.TOC_FILENAME

def _package_factory(directory):
	if not _hasTOC(directory):
		return None

	directory = os.path.abspath(directory)
	directory = directory.decode('utf-8') if isinstance(directory, bytes) else directory
	# toc_path = _TOCPath( directory )
	bucket = FilesystemBucket(directory)
	key = FilesystemKey(bucket=bucket, name=eclipse.TOC_FILENAME)
	temp_entry = FilesystemContentUnit(key=key)
	assert key.absolute_path == _TOCPath(directory) == temp_entry.filename
	package = eclipse.EclipseContentPackage(temp_entry, FilesystemContentPackage, FilesystemContentUnit)
	__traceback_info__ = directory, bucket, key, temp_entry, package
	assert package.key.bucket == bucket
	bucket.__parent__ = package

	return package

from nti.dublincore.interfaces import ILastModified

@interface.implementer(ILastModified)
class _FilesystemLibraryEnumeration(library.AbstractContentPackageEnumeration):
	"""
	A library that will examine the root to find possible content packages
	"""

	def __init__(self, root):
		self._root = root

	def _time(self, key):
		return os.stat(self._root)[key]

	@property
	def createdTime(self):
		return self._time(os.path.stat.ST_CTIME)

	@property
	def lastModified(self):
		return self._time(os.path.stat.ST_MTIME)

	def _package_factory(self, path):
		return _package_factory(path)

	def _possible_content_packages(self):
		for p in os.listdir(self._root):
			p = os.path.join(self._root, p)
			p = os.path.abspath(p)
			if os.path.isdir(p) and _hasTOC(p):
				yield p



@interface.implementer(IFilesystemContentPackageLibrary)
class EnumerateOnceFilesystemLibrary(library.ContentPackageLibrary):
	"""
	A library that will examine the root to find possible content packages
	only the very first time that it is requested to. Changes after that
	point will be ignored. The content packages and parsed
	data will be cached in memory until this library is deleted.

	This library will broadcast :class:`.IObjectCreatedEvent` and
	:class:`.IObjectAddedEvent` for content packages.
	"""

	def __init__(self, root='', **kwargs):
		if 'paths' in kwargs:
			raise TypeError("DynamicFilesystemLibrary does not accept paths, just root")

		root = root or kwargs.pop('root')
		enumeration = _FilesystemLibraryEnumeration(root)
		library.ContentPackageLibrary.__init__(self, enumeration, **kwargs)


# A measure of BWC
DynamicFilesystemLibrary = EnumerateOnceFilesystemLibrary
StaticFilesystemLibrary = library.EmptyLibrary

def CachedNotifyingStaticFilesystemLibrary(paths=()):
	if not paths:
		return library.EmptyLibrary()

	roots = {os.path.dirname(p) for p in paths}
	if len(roots) == 1:
		return EnumerateOnceFilesystemLibrary(list(roots)[0])
	raise TypeError("Unsupported use of multiple paths")
	# Though we could support it without too much trouble

@interface.implementer(IFilesystemBucket, IZContained)
class FilesystemBucket(object):
	__slots__ = (b'name', b'__parent__')

	__name__ = alias('name')
	key = alias('name')

	def __init__(self, name=None, parent=None):
		self.name = name
		self.__parent__ = parent

	def __eq__(self, other):
		try:
			return self.name == other.name
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return hash(self.name)

	def __repr__( self ):
		return "%s('%s')" % (self.__class__.__name__, self.name.encode('unicode_escape'))

@interface.implementer(IFilesystemKey, IZContained)
class FilesystemKey(object):
	# __slots__ = ('name', 'bucket') # Doesn't play well with CachedProperty

	bucket = None
	name = None

	__name__ = alias('name')
	key = alias('name')
	__parent__ = alias('bucket')


	def __init__(self, bucket=None, name=None):
		if bucket is not None:
			self.bucket = bucket
		if name is not None:
			self.name = name

	@CachedProperty('bucket', 'name')
	def absolute_path(self):
		return os.path.join(self.bucket.name, self.name) if self.bucket and self.bucket.name and self.name is not None else self.name

	def __eq__(self, other):
		try:
			return self.bucket == other.bucket and self.name == other.name
		except AttributeError:
			return NotImplemented

	def __repr__(self):
		return "<FilesystemKey '%s'>" % self.absolute_path

	def __hash__(self):
		return hash(self.absolute_path)

from .contentunit import _exist_cache
from .contentunit import _content_cache

from nti.dublincore.time_mixins import TimeProperty
class _FilesystemTime(object):
	"""
	A descriptor that caches a filesystem time, allowing
	for errors in case its accessed too early.
	"""
	def __init__( self, name, st ):
		self._st = st
		self._name = str(name)

	def __get__(self, inst, klass):
		if inst is None:
			return self

		if self._name in inst.__dict__:
			return inst.__dict__[self._name]

		try:
			val = os.stat(inst.filename)[self._st]
		except (OSError,TypeError):
			return 0
		else:
			inst.__dict__[self._name] = val
			return val

	def __set__(self, inst, val):
		pass

@interface.implementer(IFilesystemContentUnit)
class FilesystemContentUnit(ContentUnit):
	"""
	Adds the `filename` property, an alias of the `key` property
	"""

	def _get_key(self):
		return self.__dict__.get('key', None)
	def _set_key(self, nk):
		if isinstance(nk, basestring):
			# OK, the key is a simple string, meaning a path within
			# a directory.
			# TODO: Assuming one level of hierarchy
			bucket_name = os.path.dirname(nk)
			key_name = os.path.basename(nk)
			bucket = FilesystemBucket(bucket_name) if bucket_name else None
			if bucket:
				bucket.__parent__ = self
			file_key = FilesystemKey(bucket=bucket, name=key_name)
			self.__dict__[str('key')] = file_key
		else:
			self.__dict__[str('key')] = nk
	key = property(_get_key, _set_key)


	def _get_filename(self):
		return self.key.absolute_path if self.key else None
	filename = property(_get_filename, _set_key)

	@property
	def dirname(self):
		filename = self.filename
		if filename:
			return os.path.dirname(filename)


	lastModified = _FilesystemTime('lastModified', os.path.stat.ST_MTIME)
	modified = TimeProperty('lastModified', writable=False, cached=True)


	createdTime = _FilesystemTime('createdTime', os.path.stat.ST_CTIME)
	created = TimeProperty('createdTime', writable=False, cached=True)

	@repoze.lru.lru_cache(None, cache=_content_cache)
	def read_contents(self):
		try:
			with open(self.filename, 'r') as f:
				return f.read()
		except IOError:
			return None

	def get_parent_key(self):
		return FilesystemKey(bucket=self.key.bucket, name='')

	def make_sibling_key(self, sibling_name):
		__traceback_info__ = self.filename, sibling_name
		key = FilesystemKey(bucket=self.key.bucket, name=sibling_name)
		# TODO: If we get a multi-level sibling_name (relative/path/i.png),
		# should we unpack that into a bucket hierarchy? The joining
		# functions seem to work fine either way
		# TODO: If we get a URL-encoded key, should we decode it?
		assert key.absolute_path == os.path.join(os.path.dirname(self.filename), sibling_name)
		return key

	@repoze.lru.lru_cache(None, cache=_content_cache)  # first arg is ignored. This caches with the key (self, sibling_name)
	def _do_read_contents_of_sibling_entry(self, sibling_name):
		try:
			with open(self.make_sibling_key(sibling_name).absolute_path, 'r') as f:
				return f.read()
		except (OSError, IOError):
			return None

	def read_contents_of_sibling_entry(self, sibling_name):
		if self.filename:
			return self._do_read_contents_of_sibling_entry(sibling_name)

	@repoze.lru.lru_cache(None, cache=_exist_cache)
	def does_sibling_entry_exist(self, sibling_name):
		sib_key = self.make_sibling_key(sibling_name)
		return sib_key if os.path.exists(sib_key.absolute_path) else None

	def __repr__(self):
		return "<%s.%s '%s' '%s'>" % (self.__class__.__module__, self.__class__.__name__,
									  self.__name__, self.filename)


	def __eq__(self, other):
		try:
			return self.key == other.key and self.__parent__ == other.__parent__
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return hash(self.filename)

@interface.implementer(IFilesystemContentPackage)
class FilesystemContentPackage(ContentPackage, FilesystemContentUnit):
	"""
	Adds the `filename` property to the ContentPackage.
	"""

	TRANSIENT_EXCEPTIONS = (IOError,)
