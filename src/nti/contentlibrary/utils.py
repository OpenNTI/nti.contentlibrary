#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from datetime import datetime

from zope import component

from zope.intid.interfaces import IIntIds

from nti.contentlibrary import CONTENT_PACKAGE_MIME_TYPE

from nti.contentlibrary.index import IX_SITE
from nti.contentlibrary.index import IX_MIMETYPE
from nti.contentlibrary.index import get_contentlibrary_catalog

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IEditableContentPackage

from nti.recorder.interfaces import TRX_TYPE_UPDATE

from nti.recorder.interfaces import ITransactionRecordHistory

from nti.recorder.utils import decompress

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
    if catalog is None: # tests
        return ()
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

    return list(result.values())


def _include_record(record, publish_time):
    # Only want records before our timestamp and that
    # changed the package contents.
    return  record.created <= publish_time \
        and record.attributes \
        and 'contents' in record.attributes


def _get_publish_record(records, publish_time):
    records = [x for x in records if _include_record(x, publish_time)]
    result = None
    if records:
        sorted_txs = sorted(records, key=lambda x: x.created)
        result = sorted_txs[-1]
    return result


def get_snapshot_contents(package, timestamp):
    """
    For a given content package, return the package `contents` as-of
    the given timestamp.
    """
    result = None
    if not timestamp:
        return result
    history = ITransactionRecordHistory(package, None)
    if history is not None:
        records = history.query(record_type=TRX_TYPE_UPDATE)
        if records:
            # Sort and fetch the closest update to our time
            timestamp = datetime.utcfromtimestamp(timestamp)
            publish_record = _get_publish_record( records, timestamp )
            if publish_record is not None:
                publish_attrs = decompress( publish_record.external_value )
                try:
                    result = publish_attrs['contents']
                except KeyError:
                    logger.warn('No contents found (%s) (external_value=%s)',
                                 package.ntiid,
                                 publish_attrs)
    return result


def get_published_contents(package):
    """
    For a given publishable content package, return the package `contents` as-of
    the publish time.
    """
    assert IEditableContentPackage.providedBy(package)
    publish_time = package.publishLastModified
    contents = get_snapshot_contents(package, publish_time)
    return contents
