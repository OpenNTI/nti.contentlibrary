#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import re
import six
import time
import shutil
import zipfile
import tempfile
from PIL import Image
from datetime import datetime
from collections import namedtuple

from zope import component

from zope.intid.interfaces import IIntIds

from nti.coremetadata.interfaces import SYSTEM_USER_NAME

from nti.contentlibrary import HTML
from nti.contentlibrary import BUNDLE
from nti.contentlibrary import ALL_CONTENT_PACKAGE_MIME_TYPES

from nti.contentlibrary.index import IX_SITE
from nti.contentlibrary.index import IX_MIMETYPE
from nti.contentlibrary.index import get_contentlibrary_catalog

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import get_provider
from nti.ntiids.ntiids import get_specific
from nti.ntiids.ntiids import make_specific_safe

from nti.recorder.interfaces import TRX_TYPE_UPDATE

from nti.recorder.interfaces import ITransactionRecordHistory

from nti.recorder.utils import decompress

from nti.site.interfaces import IHostPolicyFolder

from nti.site.site import get_component_hierarchy_names

from nti.zodb.containers import time_to_64bit_int

#: Default NTIID provider
NTI = u'NTI'


def get_content_packages(sites=(), mime_types=None):
    """
    Return a list of :class:`.IContentPackage` objects
    based on the sites and mime types
    """
    if not sites:
        sites = get_component_hierarchy_names()
    elif isinstance(sites, six.string_types):
        sites = sites.split()
    if not mime_types:
        mime_types = ALL_CONTENT_PACKAGE_MIME_TYPES

    result = dict()
    intids = component.getUtility(IIntIds)
    catalog = get_contentlibrary_catalog()
    if catalog is None:  # tests
        return ()
    for site in sites:
        query = {
            IX_SITE: {'any_of': (site,)},
            IX_MIMETYPE: {'any_of': mime_types},
        }
        for doc_id in catalog.apply(query) or ():
            context = intids.queryObject(doc_id)
            if IContentPackage.providedBy(context) \
                    and context.ntiid not in result:
                result[context.ntiid] = context

    return list(result.values())


def _include_record(record, publish_time):
    # Only want records before our timestamp and that
    # changed the package contents.
    return record.created <= publish_time \
        and record.attributes \
        and 'contents' in record.attributes


def get_publish_record(records, publish_time):
    records = (x for x in records if _include_record(x, publish_time))
    result = None
    if records:
        sorted_txs = sorted(records, key=lambda x: x.created)
        result = sorted_txs[-1]
    return result


Snapshot = namedtuple('Snapshot', 'contents version')


def get_package_snapshot(package, timestamp=None):
    """
    For a given content package, return the package `contents` and version
    as-of the given timestamp.
    """
    result = None
    history = ITransactionRecordHistory(package, None)
    if not timestamp or history is None:
        return result
    else:
        records = history.query(record_type=TRX_TYPE_UPDATE)
        if records:
            # Sort and fetch the closest update to our time
            timestamp = datetime.utcfromtimestamp(timestamp)
            publish_record = get_publish_record(records, timestamp)
            if publish_record is not None:
                publish_attrs = decompress(publish_record.external_value)
                try:
                    result = Snapshot(publish_attrs['contents'],
                                      publish_attrs.get('version'))
                except KeyError:
                    logger.warn('No contents found (%s) (external_value=%s)',
                                package.ntiid,
                                publish_attrs)
    return result


def get_snapshot_contents(package, timestamp=None):
    """
    For a given content package, return the package `contents` as-of
    the given timestamp.
    """
    snapshot = get_snapshot_contents(package, timestamp)
    if snapshot is not None:
        return snapshot.contents
    return None


def get_published_snapshot(package):
    """
    For a given content package, return the package `contents` and version
    as-of the given timestamp.
    """
    assert IEditableContentPackage.providedBy(package)
    publish_time = package.publishLastModified
    return get_package_snapshot(package, publish_time)


def get_published_contents(package):
    """
    For a given publishable content package, return the package `contents`
    as-of the publish time or None if nothing available.
    """
    snapshot = get_published_snapshot(package)
    return snapshot.contents if snapshot is not None else None


def make_package_ntiid(provider=NTI, base=None, extra=None):
    creator = SYSTEM_USER_NAME
    current_time = time_to_64bit_int(time.time())
    if not provider:
        provider = (get_provider(base) or NTI) if base else NTI

    specific_base = get_specific(base) if base else None
    if specific_base:
        specific_base += '.%s.%s' % (creator, current_time)
    else:
        specific_base = '%s.%s' % (creator, current_time)

    if extra:
        specific_base = specific_base + ".%s" % extra
    specific = make_specific_safe(specific_base)

    ntiid = make_ntiid(nttype=HTML,
                       base=base,
                       provider=provider,
                       specific=specific)
    return ntiid


def make_content_package_ntiid(package=None, provider=NTI, base=None, extra=None):
    if IRenderableContentPackage.providedBy(package):
        specific = get_specific(base) if base else None
        if not specific:
            intids = component.getUtility(IIntIds)
            specific = '%s' % intids.getId(package)
        elif extra:
            specific += ".%s" % extra
        return make_ntiid(nttype=HTML,
                          provider=provider,
                          specific=specific)
    else:
        return make_package_ntiid(provider, base, extra)


def make_content_package_bundle_ntiid(bundle=None, provider=NTI, base=None, extra=None):
    specific = get_specific(base) if base else None
    if not specific:
        intids = component.getUtility(IIntIds)
        specific = '%s' % intids.getId(bundle)
    elif extra:
        specific += ".%s" % extra
    return make_ntiid(nttype=BUNDLE,
                      provider=provider,
                      specific=specific)


def get_content_package_site(context):
    folder = IHostPolicyFolder(IContentUnit(context, None), None)
    return folder.__name__ if folder is not None else None  # folder name


get_content_package_site_name = get_content_package_site


def get_content_package_site_registry(context):
    folder = IHostPolicyFolder(IContentUnit(context, None), None)
    return folder.getSiteManager() if folder is not None else None


def is_valid_presentation_assets_source(source):
    tmpdirs = []
    result = False
    try:
        if hasattr(source, "read"):
            tmpdir = tempfile.mkdtemp()
            name = os.path.join(tmpdir, 'source.zip')
            with open(name, "wb") as fp:
                fp.read(source.read())
            source = name
            tmpdirs.append(tmpdir)
        if isinstance(source, six.string_types):
            tmpdir = None
            if os.path.isfile(source):
                if zipfile.is_zipfile(source):
                    tmpdir = tempfile.mkdtemp()
                    z_file = zipfile.ZipFile(source)
                    z_file.extractall(path=tmpdir)
                    files = os.listdir(tmpdir)
                    if files and len(files) == 1:
                        source = os.path.join(tmpdir, files[0])
                    else:
                        source = tmpdir
            if not os.path.isdir(source):
                tmpdirs.append(tmpdir) if tmpdir else ()
            else:  # directory
                targets = []
                result = source
                for name in os.listdir(source):
                    if name.startswith('.'):
                        continue
                    # validate target
                    target = os.path.join(source, name)
                    if not os.path.isdir(target):
                        logger.error(
                            "%s is not valid target directory", target)
                        result = False
                        break
                    targets.append(target)
                # inside each target check versions
                versions = []
                if result:
                    for path in targets:
                        for name in os.listdir(path):
                            if name.startswith('.'):
                                continue
                            if not re.match('v\d+$', name):
                                result = False
                                logger.error("%s is not a valid version directory name",
                                             name)
                                break
                            version = os.path.join(target, name)
                            if not os.path.isdir(version):
                                result = False
                                logger.error("%s is not valid version directory",
                                             version)
                                break
                            versions.append(version)
                # if no error check asset directories
                if result:
                    for path in versions:
                        for name in os.listdir(path):
                            if name.startswith('.'):
                                continue
                            name = os.path.join(path, name)
                            try:
                                Image.open(name)
                            except Exception:
                                result = False
                                logger.error("%s is not a valid image file",
                                             name)
                                break
        return result
    finally:
        for path in tmpdirs:
            shutil.rmtree(path, ignore_errors=True)
