#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic implementations of IContentUnit functions

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import gzip
import time
import rfc822
import numbers
import datetime
from six import StringIO

import webob.datetime_utils

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

import repoze.lru

from nti.contentlibrary import eclipse
from nti.contentlibrary import library

from nti.contentlibrary.contentunit import ContentUnit
from nti.contentlibrary.contentunit import ContentPackage

from nti.contentlibrary.interfaces import IS3Key
from nti.contentlibrary.interfaces import IS3Bucket
from nti.contentlibrary.interfaces import IS3ContentUnit
from nti.contentlibrary.interfaces import IS3ContentPackage
from nti.contentlibrary.interfaces import IDelimitedHierarchyEntry
from nti.contentlibrary.interfaces import IEclipseContentPackageFactory

# We mark all of the classes declared here as
# non-pickalable, because we don't have their persistence
# worked out yet.
from nti.externalization.persistence import NoPickle

from nti.property.property import alias

# Make the boto classes fit better with Zope, including making them
# ILocation like and giving them interfaces
import boto.s3.key
import boto.s3.bucket
from boto.exception import AWSConnectionError

interface.classImplements(boto.s3.key.Key, IS3Key)
interface.classImplements(boto.s3.bucket.Bucket, IS3Bucket)


class _WithName:  # NOTE: Not new-style
    __name__ = alias('name')


class _WithExists:  # NOTE: Not new-style

    def exists(self, *args, **kwargs):
        try:
            # if we can list anything we exists
            self.get_all_keys(max_keys=1)
            return True
        except Exception: # connection errors?
            return False

boto.s3.bucket.Bucket.__bases__ += (_WithName, _WithExists)
boto.s3.bucket.Bucket.__parent__ = alias('connection')

boto.s3.key.Key.__bases__ += _WithName,
boto.s3.key.Key.__parent__ = alias('bucket')


class NameEqualityKey(boto.s3.key.Key):
    """
    A class that tests for equality based on the name and bucket. Two keys with
    the same name in the same bucket will be equal. The same name across
    buckets will not be equal.

    .. caution:: This is only useful with the :class:`NameEqualityBucket`.
            This does not take the connection into account, and
            hence is somewhat dangerous. Only use it if there will be one
            set of credentials in use.
    """

    # Not taking the connection into account because I don't have time to
    # verify its equality conditions.

    def __eq__(self, other):
        try:
            return self is other \
                or (self.name == other.name and self.bucket == other.bucket)
        except AttributeError:  # pragma: no cover
            return NotImplemented

    def __hash__(self):
        return hash(self.name) + 37 + hash(self.bucket)


class NameEqualityBucket(boto.s3.bucket.Bucket):
    """
    A class that tests for equality based on the name.

    .. caution:: This does not take the connection into account, and
            hence is somewhat dangerous. Only use it if there will be one
            set of credentials in use.
    """

    def __init__(self, connection=None, name=None, key_class=NameEqualityKey):
        super(NameEqualityBucket, self).__init__(connection=connection,
                                                 name=name,
                                                 key_class=key_class)

    def __eq__(self, other):
        try:
            return self is other or self.name == other.name
        except AttributeError:  # pragma: no cover
            return NotImplemented

    def __hash__(self):
        return hash(self.name) + 37


def key_last_modified(key):
    """
    Return the last modified value of the key in some form thats actually
    useful, not a goddamn arbitrary format string.

    :return: A float, or None.
    """
    __traceback_info__ = key, key.last_modified
    if isinstance(key.last_modified, numbers.Number):
        return key.last_modified  # Mainly for tests
    result = rfc822.parsedate_tz(key.last_modified)
    if result is not None:
        result = rfc822.mktime_tz(result)
        # This is supposed to be coming in rfc822 format (see boto.s3.key)
        # But it doesn't always. So try to parse it ourself if we have to
    elif key.last_modified:
        # 2012-05-12T23:15:24.000Z
        result = datetime.datetime.strptime(key.last_modified,
                                            '%Y-%m-%dT%H:%M:%S.%fZ')
        result = result.replace(tzinfo=webob.datetime_utils.UTC)
        result = time.mktime(result.timetuple())
    return result

from nti.contentlibrary.contentunit import _exist_cache
from nti.contentlibrary.contentunit import _content_cache


# first arg is ignored. This caches with the key (key,)
@repoze.lru.lru_cache(None, cache=_content_cache)
def _read_key(key):
    data = None
    if key:
        data = key.get_contents_as_string()
        if key.content_encoding == 'gzip':
            stream = StringIO(data)
            gzip_stream = gzip.GzipFile(fileobj=stream, mode='rb')
            data = gzip_stream.read()
            gzip_stream.close()
            stream.close()
    return data


@component.adapter(IS3Key)
@interface.implementer(IDelimitedHierarchyEntry)
class _KeyDelimitedHierarchyEntry(object):

    __slots__ = ('key',)

    def __init__(self, key):
        self.key = key

    def make_sibling_key(self, sibling_name):
        split = self.key.name.split('/')
        split[-1] = sibling_name
        new_key = type(self.key)(bucket=self.key.bucket, name='/'.join(split))
        return new_key

    def get_parent_key(self):
        split = self.key.name.split('/')
        parent_part = split[0:-1]
        new_key = type(self.key)(bucket=self.key.bucket, 
                                 name='/'.join(parent_part))
        return new_key

    def read_contents(self):
        return _read_key(self.key)

    def read_contents_of_sibling_entry(self, sibling_name):
        new_key = self.does_sibling_entry_exist(sibling_name)
        return _read_key(new_key)

    def does_sibling_entry_exist(self, sibling_name):
        """
        :return: Either a Key containing some information about an existing
                sibling (and which is True) or None for an absent sibling (False).
        """
        bucket = self.key.bucket
        sib_key = self.make_sibling_key(sibling_name).name
        try:
            return bucket.get_key(sib_key)
        except AttributeError:  # seen when we are not connected
            exc_info = sys.exc_info()
            raise AWSConnectionError("No connection"), None, exc_info[2]


@NoPickle
@interface.implementer(IS3ContentUnit)
class BotoS3ContentUnit(ContentUnit):
    """

    .. py:attribute:: key

            The :class:`boto.s3.key.Key` for this unit.

    """

    # Note: Boto s3.key.Key does not have good == or hash semantics, both are
    # identity based
    key = None

    def _connect_key(self):
        """
        Ensure the key, which may have been created in a disconnected
        state, is open enough for the purposes of this object.
        """
        if self.key and self.key.last_modified is None and self.key.bucket:
            self.key.open()

    @Lazy
    def lastModified(self):
        try:
            self._connect_key()
        except boto.exception.StorageResponseError:
            # The key is probably gone, most likely because the bucket
            # is in the process of being updated.
            logger.debug("Ignoring storage error accessing lastModified",
                         exc_info=True)
            # Return a flag value (so that `modified` doesn't blow up). This gets cached. Alternatively,
            # we could raise AttributeError...this is mostly used dynamically with getattr and so
            # would effectively be a None?
            return -1

        return key_last_modified(self.key)

    @Lazy
    def modified(self):
        return datetime.datetime.utcfromtimestamp(self.lastModified)

    created = modified

    def make_sibling_key(self, sibling_name):
        entry = IDelimitedHierarchyEntry(self.key)
        return entry.make_sibling_key(sibling_name)

    def get_parent_key(self):
        return IDelimitedHierarchyEntry(self.key).get_parent_key()

    def read_contents(self):
        return IDelimitedHierarchyEntry(self.key).read_contents()

    def read_contents_of_sibling_entry(self, sibling_name):
        if self.key:
            entry = IDelimitedHierarchyEntry(self.key)
            return entry.read_contents_of_sibling_entry(sibling_name)

    # first arg is ignored. This caches with the key (self, sibling_name)
    @repoze.lru.lru_cache(None, cache=_exist_cache)
    def does_sibling_entry_exist(self, sibling_name):
        entry = IDelimitedHierarchyEntry(self.key)
        return entry.does_sibling_entry_exist(sibling_name)


@NoPickle
@interface.implementer(IS3ContentPackage)
class BotoS3ContentPackage(ContentPackage, BotoS3ContentUnit):

    TRANSIENT_EXCEPTIONS = (AWSConnectionError,)

    # XXX: Note that this needs the same lastModified fixes as
    # the filesystem version


def package_factory(key, _package_factory=None, _unit_factory=None):

    _unit_factory = _unit_factory or BotoS3ContentUnit
    _package_factory = _package_factory or BotoS3ContentPackage

    toc_key = key.bucket.get_key((key.name + '/' +
                                  eclipse.TOC_FILENAME).replace('//', '/'))

    if toc_key:
        temp_entry = BotoS3ContentUnit(key=toc_key)
        return eclipse.EclipseContentPackage(temp_entry,
                                             _package_factory,
                                             _unit_factory)
_package_factory = package_factory


@interface.implementer(IEclipseContentPackageFactory)
class _EclipseContentPackageFactory(object):

    __slots__ = ()

    def __init__(self, *args):
        pass

    def new_instance(self, item, package_factory=None, unit_factory=None):
        return package_factory(item, package_factory, unit_factory)


@NoPickle
class _BotoS3BucketContentLibraryEnumeration(library.AbstractContentPackageEnumeration):

    def __init__(self, bucket):
        """
        :param bucket: The bucket to enumerate.
        """
        self._bucket = bucket

    def _package_factory(self, key):
        return _package_factory(key)

    def _possible_content_packages(self):
        return list(self._bucket.list(delimiter='/'))


@NoPickle
class BotoS3BucketContentLibrary(library.GlobalContentPackageLibrary):
    """
    Enumerates the first level of a '/' delimited bucket and treats each
    entry as a possible content package. Content packages are cached.

    .. warning:: This is completely static right now, enumerated just once.
            We need some level of dynamism here.

    .. warning:: We probably generate content units that are invalid and incapable of
            getting their last modified dates when hrefs contain fragment identifiers, since
            those do not correspond to files in the filesystem or objects in the bucket.
    """

    def __init__(self, bucket):
        enum = _BotoS3BucketContentLibraryEnumeration(bucket)
        library.GlobalContentPackageLibrary.__init__(self, enum)
