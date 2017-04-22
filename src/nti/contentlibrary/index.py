#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
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

from nti.traversal.location import find_interface

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
IX_CREATEDTIME = 'createdTime'
IX_LASTMODIFIED = 'lastModified'
IX_PUBLISH_LASTMODIFIED = 'publishLastModified'


class ValidatingSiteName(object):

    __slots__ = (b'site',)

    def __init__(self, obj, default=None):
        if IContentUnit.providedBy(obj):
            folder = find_interface(obj, IHostPolicyFolder)
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

    __slots__ = (b'children',)

    def __init__(self, obj, default=None):
        if IContentUnit.providedBy(obj):
            self.children = tuple(x.ntiid for x in obj.children or ())

    def __reduce__(self):
        raise TypeError()


class ChildrenIndex(AttributeSetIndex):
    default_field_name = 'children'
    interface = default_interface = ValidatingChildren


class ValidatingCreator(object):

    __slots__ = (b'creator',)

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


class CreatedTimeRawIndex(RawIntegerValueIndex):
    pass


def CreatedTimeIndex(family=None):
    return NormalizationWrapper(field_name='createdTime',
                                interface=IContentUnit,
                                index=CreatedTimeRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


class LastModifiedRawIndex(RawIntegerValueIndex):
    pass


def LastModifiedIndex(family=None):
    return NormalizationWrapper(field_name='lastModified',
                                interface=IContentUnit,
                                index=LastModifiedRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


class PublishLastModifiedRawIndex(RawIntegerValueIndex):
    pass


def PublishLastModifiedIndex(family=None):
    return NormalizationWrapper(field_name='publishLastModified',
                                interface=IEditableContentUnit,
                                index=PublishLastModifiedRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


class LibraryCatalog(Catalog):
    family = BTrees.family64


def get_contentlibrary_catalog():
    return component.queryUtility(ICatalog, name=CATALOG_INDEX_NAME)


def create_library_catalog(catalog=None, family=None):
    catalog = LibraryCatalog() if catalog is None else catalog
    for name, clazz in ((IX_SITE, SiteIndex),
                        (IX_NTIID, NTIIDIndex),
                        (IX_CREATOR, CreatorIndex),
                        (IX_CHILDREN, ChildrenIndex),
                        (IX_MIMETYPE, MimeTypeIndex),
                        (IX_CREATEDTIME, CreatedTimeIndex),
                        (IX_LASTMODIFIED, LastModifiedIndex),
                        (IX_PUBLISH_LASTMODIFIED, PublishLastModifiedIndex)):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index
    return catalog


def install_library_catalog(site_manager_container, intids=None):
    lsm = site_manager_container.getSiteManager()
    intids = lsm.getUtility(IIntIds) if intids is None else intids
    catalog = lsm.queryUtility(ICatalog, name=CATALOG_INDEX_NAME)
    if catalog is not None:
        return catalog

    catalog = LibraryCatalog()
    locate(catalog, site_manager_container, CATALOG_INDEX_NAME)
    intids.register(catalog)
    lsm.registerUtility(catalog, provided=ICatalog, name=CATALOG_INDEX_NAME)

    catalog = create_library_catalog(catalog=catalog, family=intids.family)
    for index in catalog.values():
        intids.register(index)
    return catalog
