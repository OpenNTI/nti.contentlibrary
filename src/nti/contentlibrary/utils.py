#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import six
import sys

from boto.exception import AWSConnectionError

from zope import component

from zope.intid.interfaces import IIntIds

from nti.contentlibrary import CONTENT_PACKAGE_MIME_TYPE

from nti.contentlibrary.index import IX_SITE
from nti.contentlibrary.index import IX_MIMETYPE
from nti.contentlibrary.index import get_contentlibrary_catalog

from nti.contentlibrary.interfaces import IContentPackage, IFilesystemKey

from nti.site.site import get_component_hierarchy_names

# index


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

# file system


def make_file_system_sibling_key(key, sibling_name):
    # Because keys cache things like dates and contents, it is useful
    # to return the same instance

    filename = key.absolute_path
    __traceback_info__ = filename, sibling_name
    assert bool(sibling_name)
    assert not sibling_name.startswith('/')

    # At this point, everything should already be URL-decoded,
    # (and fragments removed) and unicode
    # If we get a multi-segment path, we need to deconstruct it
    # into bucket parts to be sure that it externalizes
    # correctly.
    parent = key.bucket
    parts = sibling_name.split('/')
    for part in parts[:-1]:
        parent = type(key.bucket)(bucket=parent, name=part)

    key = type(key)(bucket=parent, name=parts[-1])

    dirname = os.path.dirname(filename)
    assert key.absolute_path == os.path.join(dirname, *parts)
    return key


def does_file_system_sibling_entry_exist(key, sibling_name):
    sib_key = make_file_system_sibling_key(sibling_name)
    return sib_key if os.path.exists(sib_key.absolute_path) else None


# boto

def make_boto_sibling_key(key, sibling_name):
    split = key.name.split('/')
    split[-1] = sibling_name
    new_key = type(key)(bucket=key.bucket, name='/'.join(split))
    return new_key


def does_boto_sibling_entry_exist(key, sibling_name):
    bucket = key.bucket
    sib_key = make_boto_sibling_key(sibling_name).name
    try:
        return bucket.get_key(sib_key)
    except AttributeError:  # seen when we are not connected
        exc_info = sys.exc_info()
        raise AWSConnectionError("No connection"), None, exc_info[2]

# general


def make_sibling_key(key, sibling_name):
    if IFilesystemKey.providedBy(key):
        return make_file_system_sibling_key(key, sibling_name)
    else:
        return make_boto_sibling_key(key, sibling_name)


def does_sibling_entry_exist(key, sibling_name):
    if IFilesystemKey.providedBy(key):
        return does_file_system_sibling_entry_exist(key, sibling_name)
    else:
        return does_boto_sibling_entry_exist(key, sibling_name)
