#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from persistent.list import PersistentList

from ZODB.POSException import ConnectionStateError

from zope import interface

from zope.cachedescriptors.property import readproperty

from zope.container.ordered import OrderedContainer

from zope.dublincore.interfaces import IDCTimes

from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.base._compat import text_

from nti.contentlibrary.bucket import AbstractKey
from nti.contentlibrary.bucket import AbstractBucket

from nti.contentlibrary.contentunit import ContentUnit
from nti.contentlibrary.contentunit import ContentPackage

from nti.contentlibrary.interfaces import INoAutoSync
from nti.contentlibrary.interfaces import IContentRendered
from nti.contentlibrary.interfaces import IEditableContentUnit
from nti.contentlibrary.interfaces import IPersistentContentUnit
from nti.contentlibrary.interfaces import IRenderableContentUnit
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IDelimitedHierarchyEntry
from nti.contentlibrary.interfaces import IPersistentContentPackage
from nti.contentlibrary.interfaces import IRenderableContentPackage
from nti.contentlibrary.interfaces import IWritableDelimitedHierarchyKey
from nti.contentlibrary.interfaces import IEnumerableDelimitedHierarchyBucket
from nti.contentlibrary.interfaces import IDelimitedHierarchyEditableContentUnit
from nti.contentlibrary.interfaces import IDelimitedHierarchyEditableContentPackage

from nti.publishing.interfaces import INoPublishLink

from nti.publishing.mixins import PublishableMixin

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.ntiids.oids import to_external_ntiid_oid

from nti.property.property import alias

from nti.recorder.mixins import RecordableMixin

from nti.schema.fieldproperty import createDirectFieldProperties

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IDCTimes)
class TimesMixin(PersistentCreatedModDateTrackingObject):

    created = alias('createdTime')
    modified = alias('lastModified')

    def __init__(self, *args, **kwargs):  # pylint: disable=useless-super-delegation
        super(TimesMixin, self).__init__(*args, **kwargs)


@interface.implementer(IWritableDelimitedHierarchyKey)
class PersistentHierarchyKey(TimesMixin, AbstractKey):
    createDirectFieldProperties(IWritableDelimitedHierarchyKey)

    def readContents(self):
        return self.data
    read_contents = readContents

    def writeContents(self, data):
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        self.data = data  # pylint: disable=attribute-defined-outside-init
    write_contents = writeContents


@interface.implementer(IEnumerableDelimitedHierarchyBucket)
class PersistentHierarchyBucket(TimesMixin,
                                AbstractBucket,
                                OrderedContainer):

    _key_type = PersistentHierarchyKey

    def __init__(self, *args, **kwargs):  # pylint: disable=super-init-not-called
        OrderedContainer.__init__(self)
        AbstractBucket.__init__(self, *args, **kwargs)

    def enumerateChildren(self):
        return list(self.values())
    enumerate_children = enumerateChildren

    def getChildNamed(self, name):
        return self.get(name)
    get_child_named = getChildNamed

    def __setitem__(self, key, value):
        self.updateLastMod()
        return OrderedContainer.__setitem__(self, key, value)

    def __delitem__(self, key):
        OrderedContainer.__delitem__(self, key)
        self.updateLastMod()


_marker = object()


@interface.implementer(IPersistentContentUnit,
                       IEditableContentUnit,
                       INoPublishLink)
class PersistentContentUnit(RecordableMixin,
                            PublishableMixin,
                            TimesMixin,
                            ContentUnit):
    """
    A persistent version of a content unit.
    """
    mime_type = mimeType = 'application/vnd.nextthought.persistentcontentunit'

    _key_type = PersistentHierarchyKey

    children_iterable_factory = PersistentList

    ContentsLastModified = 0
    contents_last_modified = alias("ContentsLastModified")

    icon = FP(IEditableContentUnit['icon'])

    def __init__(self, *args, **kwargs):
        super(PersistentContentUnit, self).__init__(*args, **kwargs)
        self.contents_key = self._key_type(name=u"contents")

    @readproperty
    def key(self):
        return self.contents_key

    def read_contents(self):
        return self.contents_key.readContents()
    readContents = read_contents

    def write_contents(self, data=None, contentType=_marker):
        self.contents_last_modified = time.time()
        self.contents_key.write_contents(data)
        if contentType is not _marker:
            self.contentType = contentType
    writeContents = write_contents

    contents = property(read_contents, write_contents)

    def get_content_type(self):
        return self.contents_key.contentType
    getContentType = get_content_type

    def set_content_type(self, contentType):
        # pylint: disable=attribute-defined-outside-init
        self.contents_key.contentType = contentType
    setContentType = set_content_type

    contentType = property(get_content_type, set_content_type)

    def update_version(self, *args, **kawrgs):
        # Nothing needed since we rely on ContentsLastModified
        pass

    @readproperty
    def version(self):
        return text_(self.ContentsLastModified)

    def publish(self, *args, **kwargs):
        # Override our mixin to allow continuous publishes.
        self.do_publish(*args, **kwargs)

    def __repr__(self):
        try:
            return super(PersistentContentUnit, self).__repr__()
        except ConnectionStateError:
            return object.__repr__(self)


@interface.implementer(IPersistentContentPackage,
                       IEditableContentPackage,
                       INoAutoSync)
class PersistentContentPackage(PersistentContentUnit, ContentPackage):
    """
    A persistent content package.
    """
    mime_type = mimeType = 'application/vnd.nextthought.persistentcontentpackage'

    index_last_modified = -1
    indexLastModified = alias("index_last_modified")


@interface.implementer(IRenderableContentUnit,
                       IDelimitedHierarchyEditableContentUnit)
class RenderableContentUnit(PersistentContentUnit):
    """
    A renderable content unit.
    """
    createDirectFieldProperties(IRenderableContentUnit)

    mime_type = mimeType = 'application/vnd.nextthought.renderablecontentunit'

    @readproperty
    def ntiid(self):
        return to_external_ntiid_oid(self)

    @property
    def has_key(self):
        return IContentRendered.providedBy(self) and self.key is not None

    def read_contents(self):
        if self.has_key:
            entry = IDelimitedHierarchyEntry(self.key, None)
            # pylint: disable=too-many-function-args
            return entry.read_contents() if entry is not None else None
        return super(RenderableContentUnit, self).read_contents()

    def get_parent_key(self):
        if self.has_key:
            entry = IDelimitedHierarchyEntry(self.key, None)
            # pylint: disable=too-many-function-args
            return entry.get_parent_key() if entry is not None else None

    def make_sibling_key(self, sibling_name):
        if self.has_key:
            entry = IDelimitedHierarchyEntry(self.key, None)
            # pylint: disable=too-many-function-args
            return entry is not None and entry.make_sibling_key(sibling_name)

    def read_contents_of_sibling_entry(self, sibling_name):
        if self.has_key:
            entry = IDelimitedHierarchyEntry(self.key, None)
            # pylint: disable=too-many-function-args
            return entry is not None and entry.read_contents_of_sibling_entry(sibling_name)

    def does_sibling_entry_exist(self, sibling_name):
        if self.has_key:
            entry = IDelimitedHierarchyEntry(self.key, None)
            # pylint: disable=too-many-function-args
            return entry is not None and entry.does_sibling_entry_exist(sibling_name)


@interface.implementer(IRenderableContentPackage,
                       IDelimitedHierarchyEditableContentPackage)
class RenderableContentPackage(RenderableContentUnit,
                               PersistentContentPackage):
    """
    A renderable content package.
    """
    createDirectFieldProperties(IRenderableContentPackage)

    mime_type = mimeType = 'application/vnd.nextthought.renderablecontentpackage'
