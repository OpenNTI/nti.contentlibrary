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

from nti.contentlibrary.bucket import AbstractKey
from nti.contentlibrary.bucket import AbstractBucket

from nti.contentlibrary.contentunit import ContentUnit
from nti.contentlibrary.contentunit import ContentPackage

from nti.contentlibrary.interfaces import INoAutoSync
from nti.contentlibrary.interfaces import IDelimitedHierarchyKey
from nti.contentlibrary.interfaces import IPersistentContentUnit
from nti.contentlibrary.interfaces import IPersistentContentPackage
from nti.contentlibrary.interfaces import IEnumerableDelimitedHierarchyBucket

from nti.coremetadata.interfaces import ITitledContent

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.property.property import alias


@interface.implementer(IDCTimes)
class _TimesMixin(PersistentCreatedModDateTrackingObject):
    created = alias('createdTime')
    modified = alias('lastModified')

    def __init__(self, *args, **kwargs):
        super(_TimesMixin, self).__init__(*args, **kwargs)
        

@interface.implementer(IDelimitedHierarchyKey)
class PersistentHierarchyKey(AbstractKey,
                             _TimesMixin,
                             ITitledContent):

    _contents = None
    data = alias('_contents')

    def __init__(self, contents, *args, **kwargs):
        super(PersistentHierarchyKey, self).__init__(*args, **kwargs)
        self._contents = contents

    def readContents(self):
        return self._contents
    read_contents = readContents


@interface.implementer(IEnumerableDelimitedHierarchyBucket)
class PersistentHierarchyBucket(AbstractBucket,
                                # order matters
                                _TimesMixin,
                                OrderedContainer):

    def enumerateChildren(self):
        return self.values()
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


@interface.implementer(IPersistentContentUnit)
class PersistentContentUnit(_TimesMixin, ContentUnit):
    """
    A persistent version of a content unit.
    """

    def __repr__(self):
        try:
            return super(PersistentContentUnit, self).__repr__()
        except ConnectionStateError:
            return object.__repr__(self)


@interface.implementer(IPersistentContentPackage, INoAutoSync)
class PersistentContentPackage(_TimesMixin, ContentPackage):
    """
    A persistent content package.
    """

    def __repr__(self):
        try:
            return super(PersistentContentPackage, self).__repr__()
        except ConnectionStateError:
            return object.__repr__(self)
