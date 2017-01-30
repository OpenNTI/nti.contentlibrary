#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.cachedescriptors.property import readproperty

from zope.container.ordered import OrderedContainer

from zope.dublincore.interfaces import IDCTimes

from ZODB.POSException import ConnectionStateError

from nti.coremetadata.mixins import RecordableMixin
from nti.coremetadata.mixins import PublishableMixin

from nti.contentlibrary.bucket import AbstractKey
from nti.contentlibrary.bucket import AbstractBucket

from nti.contentlibrary.contentunit import ContentUnit
from nti.contentlibrary.contentunit import ContentPackage

from nti.contentlibrary.interfaces import INoAutoSync
from nti.contentlibrary.interfaces import IEditableContentUnit
from nti.contentlibrary.interfaces import IPersistentContentUnit
from nti.contentlibrary.interfaces import IRenderableContentUnit
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IPersistentContentPackage
from nti.contentlibrary.interfaces import IRenderableContentPackage
from nti.contentlibrary.interfaces import IWritableDelimitedHierarchyKey
from nti.contentlibrary.interfaces import IEnumerableDelimitedHierarchyBucket

from nti.coremetadata.interfaces import INoPublishLink

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties


@interface.implementer(IDCTimes)
class TimesMixin(PersistentCreatedModDateTrackingObject):

    created = alias('createdTime')
    modified = alias('lastModified')

    def __init__(self, *args, **kwargs):
        super(TimesMixin, self).__init__(*args, **kwargs)


@interface.implementer(IWritableDelimitedHierarchyKey)
class PersistentHierarchyKey(TimesMixin, AbstractKey):
    createDirectFieldProperties(IWritableDelimitedHierarchyKey)

    def readContents(self):
        return self.data
    read_contents = readContents

    def writeContents(self, data):
        self.data = data
    write_contents = writeContents


@interface.implementer(IEnumerableDelimitedHierarchyBucket)
class PersistentHierarchyBucket(TimesMixin,
                                AbstractBucket,
                                OrderedContainer):

    _key_type = PersistentHierarchyKey

    def __init__(self, *args, **kwargs):
        OrderedContainer.__init__(self)
        AbstractBucket.__init__(*args, **kwargs)

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


@interface.implementer(IPersistentContentUnit, IEditableContentUnit, INoPublishLink)
class PersistentContentUnit(RecordableMixin, PublishableMixin, TimesMixin, ContentUnit):
    """
    A persistent version of a content unit.
    """
    mime_type = mimeType = u'application/vnd.nextthought.persistentcontentunit'

    _key_type = PersistentHierarchyKey
    
    def __init__(self, *args, **kwargs):
        super(PersistentContentUnit, self).__init__(*args, **kwargs)
        self.contents_key = self._key_type(name="contents")

    @readproperty
    def key(self):
        return self.contents_key

    def read_contents(self):
        return self.contents_key.readContents()
    readContents = read_contents

    def write_contents(self, data=None, contentType=_marker):
        self.contents_key.write_contents(data)
        if contentType is not _marker:
            self.contentType = contentType
    writeContents = write_contents

    content = property(read_contents, write_contents)

    def get_content_type(self):
        return self.contents_key.contentType
    getContentType = get_content_type

    def set_content_type(self, contentType):
        self.contents_key.contentType = contentType
    setContentType = set_content_type

    contentType = property(get_content_type, set_content_type)

    def read_contents_of_sibling_entry(self, name):
        pass

    def __repr__(self):
        try:
            return super(PersistentContentUnit, self).__repr__()
        except ConnectionStateError:
            return object.__repr__(self)


@interface.implementer(IPersistentContentPackage, IEditableContentPackage, INoAutoSync)
class PersistentContentPackage(PersistentContentUnit, ContentPackage):
    """
    A persistent content package.
    """

    mime_type = mimeType = u'application/vnd.nextthought.persistentcontentpackage'


@interface.implementer(IRenderableContentUnit)
class RenderableContentUnit(PersistentContentUnit):
    """
    A renderable content unit.
    """
    createDirectFieldProperties(IRenderableContentUnit)

    mime_type = mimeType = u'application/vnd.nextthought.renderablecontentunit'

@interface.implementer(IRenderableContentPackage)
class RenderableContentPackage(RenderableContentUnit, PersistentContentPackage):
    """
    A renderable content package.
    """
    createDirectFieldProperties(IRenderableContentPackage)

    mime_type = mimeType = u'application/vnd.nextthought.renderablecontentpackage'
