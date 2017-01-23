#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Objects for creating IContentLibrary objects based on the filesystem.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

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
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IPersistentContentPackage
from nti.contentlibrary.interfaces import IWritableDelimitedHierarchyKey
from nti.contentlibrary.interfaces import IEnumerableDelimitedHierarchyBucket

from nti.coremetadata.interfaces import ITitledContent

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.property.property import alias


@interface.implementer(IDCTimes)
class TimesMixin(PersistentCreatedModDateTrackingObject):

    created = alias('createdTime')
    modified = alias('lastModified')

    def __init__(self, *args, **kwargs):
        super(TimesMixin, self).__init__(*args, **kwargs)


@interface.implementer(IWritableDelimitedHierarchyKey)
class PersistentHierarchyKey(TimesMixin,
                             AbstractKey,
                             ITitledContent):

    _contents = None

    def __init__(self, *args, **kwargs):
        contents = kwargs.pop('contents', None)
        super(PersistentHierarchyKey, self).__init__(*args, **kwargs)
        self.data = contents

    def readContents(self):
        return self._contents
    read_contents = readContents

    def writeContents(self, data):
        self._contents = data
    write_contents = writeContents

    data = property(readContents, writeContents)


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


@interface.implementer(IPersistentContentUnit, IEditableContentUnit)
class PersistentContentUnit(RecordableMixin, PublishableMixin, TimesMixin, ContentUnit):
    """
    A persistent version of a content unit.
    """

    def __init__(self, *args, **kwargs):
        super(PersistentContentUnit, self).__init__(*args, **kwargs)
        if self.key is None:
            self.key = PersistentHierarchyKey()

    def read_contents(self):
        return self.key.readContents()
    readContents = read_contents

    def write_contents(self, data=None):
        return self.key.write_contents(data)
    writeContents = write_contents

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

    def __repr__(self):
        try:
            return super(PersistentContentPackage, self).__repr__()
        except ConnectionStateError:
            return object.__repr__(self)
