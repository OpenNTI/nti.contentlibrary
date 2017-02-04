#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component

from zope.intid.interfaces import IIntIds

from nti.contentlibrary import CONTENT_PACKAGE_MIME_TYPE

from nti.contentlibrary.index import IX_SITE
from nti.contentlibrary.index import IX_MIMETYPE
from nti.contentlibrary.index import get_contentlibrary_catalog

from nti.contentlibrary.interfaces import IContentPackage

from nti.site.site import get_component_hierarchy_names


def get_content_packages(sites=(), mime_types=(CONTENT_PACKAGE_MIME_TYPE,)):
    if not sites:
        sites = get_component_hierarchy_names()
    elif isinstance(sites, six.string_types):
        sites = sites.split()
    if not mime_types:
        mime_types = (CONTENT_PACKAGE_MIME_TYPE,)

    result = dict()
    intids = component.getUtility(IIntIds)
    catalog = get_contentlibrary_catalog()
    for site in sites:
        query = {
            IX_SITE: {'any_of': (site,)},
            IX_MIMETYPE: {'any_of': mime_types},
        }
        for doc_id in catalog.apply(query) or ():
            context = intids.queryObject(doc_id)
            if      IContentPackage.providedBy(context) \
                    and context.ntiid not in result:
                result[context.ntiid] = context

    return tuple(result.values())
