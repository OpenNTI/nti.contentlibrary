#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from zope.location import locate

import BTrees

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IEditableContentUnit

from nti.site.interfaces import IHostPolicyFolder

from nti.traversal.traversal import find_interface

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from nti.zope_catalog.index import AttributeSetIndex
from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import ValueIndex as RawValueIndex
from nti.zope_catalog.index import AttributeValueIndex as ValueIndex
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex

from nti.zope_catalog.string import StringTokenNormalizer

CATALOG_INDEX_NAME = 'nti.dataserver.++etc++contentlibrary.catalog'

IX_SITE = 'site'
IX_NTIID = 'ntiid'
IX_CREATOR = 'creator'
IX_MIMETYPE = 'mimeType'
IX_CHILDREN = 'children'
IX_PUBLISH_LASTMODIFIED = 'publishLastModified'


class ValidatingSiteName(object):

    __slots__ = ('site',)

    def __init__(self, obj, default=None):
        if IContentUnit.providedBy(obj):
            folder = find_interface(obj, IHostPolicyFolder, strict=False)
            if folder is not None:
                self.site = folder.__name__

    def __reduce__(self):
        raise TypeError()


class SiteIndex(ValueIndex):
    default_field_name = 'site'
    default_interface = ValidatingSiteName


class NTIIDIndex(ValueIndex):
    default_field_name = 'ntiid'
    default_interface = IContentUnit


class MimeTypeIndex(ValueIndex):
    default_field_name = 'mimeType'
    default_interface = IContentUnit


class ValidatingChildren(object):

    __slots__ = ('children',)

    def __init__(self, obj, default=None):
        if IContentUnit.providedBy(obj):
            self.children = tuple(x.ntiid for x in obj.children or ())

    def __reduce__(self):
        raise TypeError()


class ChildrenIndex(AttributeSetIndex):
    default_field_name = 'children'
    interface = default_interface = ValidatingChildren


class ValidatingCreator(object):

    __slots__ = ('creator',)

    def __init__(self, obj, default=None):
        try:
            if IContentUnit.providedBy(obj):
                creator = getattr(obj.creator, 'username', obj.creator)
                self.creator = getattr(creator, 'id', creator)
        except (AttributeError, TypeError):
            pass

    def __reduce__(self):
        raise TypeError()


def CreatorIndex(family=None):
    return NormalizationWrapper(field_name='creator',
                                interface=ValidatingCreator,
                                index=RawValueIndex(family=family),
                                normalizer=StringTokenNormalizer())


class PublishLastModifiedRawIndex(RawIntegerValueIndex):
    pass
CreatedTimeRawIndex = LastModifiedRawIndex = PublishLastModifiedRawIndex # BWC

def PublishLastModifiedIndex(family=None):
    return NormalizationWrapper(field_name='publishLastModified',
                                interface=IEditableContentUnit,
                                index=PublishLastModifiedRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())
CreatedTimeIndex = LastModifiedIndex = PublishLastModifiedIndex # BWC

class LibraryCatalog(Catalog):
    family = BTrees.family64


def get_contentlibrary_catalog(registry=component):
    return registry.queryUtility(ICatalog, name=CATALOG_INDEX_NAME)


def create_library_catalog(catalog=None, family=BTrees.family64):
    if catalog is None:
        catalog = LibraryCatalog(family=family)
    for name, clazz in ((IX_SITE, SiteIndex),
                        (IX_NTIID, NTIIDIndex),
                        (IX_CREATOR, CreatorIndex),
                        (IX_CHILDREN, ChildrenIndex),
                        (IX_MIMETYPE, MimeTypeIndex),
                        (IX_PUBLISH_LASTMODIFIED, PublishLastModifiedIndex)):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index
    return catalog


def install_library_catalog(site_manager_container, intids=None):
    lsm = site_manager_container.getSiteManager()
    intids = lsm.getUtility(IIntIds) if intids is None else intids
    catalog = get_contentlibrary_catalog(lsm)
    if catalog is not None:
        return catalog

    catalog = create_library_catalog(family=intids.family)
    locate(catalog, site_manager_container, CATALOG_INDEX_NAME)
    intids.register(catalog)
    lsm.registerUtility(catalog, 
                        provided=ICatalog,
                        name=CATALOG_INDEX_NAME)

    for index in catalog.values():
        intids.register(index)
    return catalog
