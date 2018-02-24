#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import re
import six
import time
import zlib
import base64
import shutil
import zipfile
import tempfile
from datetime import datetime
from collections import namedtuple

from PIL import Image

from zope import component

from zope.intid.interfaces import IIntIds

from nti.base._compat import bytes_

from nti.coremetadata.interfaces import SYSTEM_USER_NAME

from nti.contentlibrary import NTI
from nti.contentlibrary import HTML
from nti.contentlibrary import BUNDLE
from nti.contentlibrary import ALL_CONTENT_PACKAGE_MIME_TYPES

from nti.contentlibrary.index import IX_SITE
from nti.contentlibrary.index import IX_MIMETYPE
from nti.contentlibrary.index import get_contentlibrary_catalog

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentOperator
from nti.contentlibrary.interfaces import IContentVendorInfo
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IRenderableContentPackage
from nti.contentlibrary.interfaces import IContentPackageExporterDecorator

from nti.contentlibrary.vendorinfo import VENDOR_INFO_KEY

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import StandardInternalFields
from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.ntiids.ntiids import hash_ntiid
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
OID = StandardExternalFields.OID
NTIID = StandardExternalFields.NTIID

INTERNAL_NTIID = StandardInternalFields.NTIID

logger = __import__('logging').getLogger(__name__)


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


def check_image_directory(path):
    result = True
    for name in os.listdir(path):
        if name.startswith('.') or name.startswith('__'):
            continue
        name = os.path.join(path, name)
        if os.path.isdir(name):  #e.g. instructor-photos
            result = result and check_image_directory(name)
        else:
            try:
                Image.open(name)
            except Exception:  # pylint: disable=broad-except
                result = False
                logger.error("%s is not a valid image file",
                             name)
                break
    return result


def is_valid_presentation_assets_source(source, versions=None, tmpdirs=None):
    result = False
    tmpdirs = list() if tmpdirs is None else tmpdirs
    versions = list() if versions is None else versions
    try:
        if hasattr(source, "read"):
            tmpdir = tempfile.mkdtemp()
            tmpdirs.append(tmpdir)
            name = os.path.join(tmpdir, 'source.zip')
            with open(name, "wb") as fp:
                fp.write(source.read())
            source = name
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
                # pylint: disable=expression-not-assigned
                tmpdirs.append(tmpdir) if tmpdir else ()
            else:  # directory
                targets = []
                result = source
                for name in os.listdir(source):
                    if name.startswith('.') or name.startswith('__'):
                        continue
                    # validate target
                    target = os.path.join(source, name)
                    if not os.path.isdir(target):
                        logger.error("%s is not valid target directory",
                                     target)
                        result = False
                        break
                    targets.append(target)
                # inside each target check versions
                if result:
                    for path in targets:
                        for name in os.listdir(path):
                            if name.startswith('.') or name.startswith('__'):
                                continue
                            if not re.match(r'v\d+$', name):
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
                        if not check_image_directory(path):
                            result = False
        return result
    finally:
        for path in tmpdirs:
            shutil.rmtree(path, ignore_errors=True)


DEFAULT_VERSION = 'v1'


def make_presentation_asset_dir(catalog_source,
                                catalog_background,
                                catalog_promo,
                                catalog_cover,
                                catalog_thumbnail,
                                version=DEFAULT_VERSION):
    """
    Given the required presentation asset files, create a tmp dir source to
    hold these files, with all the appropriate structure.
    """
    if     catalog_source is None \
        or catalog_background is None \
        or catalog_promo is None \
        or catalog_cover is None \
        or catalog_thumbnail is None:
        raise ValueError('Must supply all presentation asset arguments.')

    tmpdir = os.path.join(tempfile.mkdtemp(), 'presentation-assets')
    os.makedirs(tmpdir)
    ipad_dir = os.path.join(tmpdir, 'iPad', version)
    webapp_dir = os.path.join(tmpdir, 'webapp', version)
    shared_dir = os.path.join(tmpdir, 'shared', version)
    os.makedirs(ipad_dir)
    os.makedirs(webapp_dir)
    os.makedirs(shared_dir)

    for source_file, filenames in ((catalog_source, ('client_image_source.png',)),
                                   (catalog_background, ('background.png',)),
                                   (catalog_promo, ('course-promo-large-16x9.png',)),
                                   (catalog_cover, ('contentpackage-landing-232x170.png',
                                                    'course-cover-232x170.png',
                                                    'contentpackage-cover-256x156.png')),
                                   (catalog_thumbnail, ('contentpackage-thumb-60x60.png',))):
        for filename in filenames:
            # Store the file in our shared directory
            shared_dest = os.path.join(shared_dir, filename)
            source_file.seek(0)
            with open(shared_dest, 'wb') as target:
                target.write(source_file.read())

            # Now link in our client directories  Note: this may create files
            # not needed by particular clients, but it's easiest.
            for client_dir in (webapp_dir, ipad_dir):
                rel_shared_dest = os.path.relpath(shared_dest, client_dir)
                client_target = os.path.join(client_dir, filename)
                os.symlink(rel_shared_dest, client_target)
    return tmpdir


def get_content_vendor_info(context, create=True):
    result = None
    if create:
        result = IContentVendorInfo(context, None)
    else:
        try:
            if IContentPackage.providedBy(context):
                # pylint: disable=protected-access
                result = context._package_vendor_info
            else:
                annotations = context.__annotations__
                result = annotations.get(VENDOR_INFO_KEY, None)
        except AttributeError:
            pass
    return result


def decode_content(content, safe=False):
    result = content
    try:
        if result:
            decoded = base64.b64decode(result)
            result = bytes_(zlib.decompress(decoded))
    except Exception:  # pylint: disable=broad-except
        if not safe:
            raise
    return result


def operate_content(content, context=None, **kwargs):
    for operator in component.subscribers((context,), IContentOperator):
        content = operator.operate(content, context, **kwargs)
    return content


def operate_encode_content(content, context=None, **kwargs):
    content = operate_content(content, context, **kwargs)
    return base64.b64encode(zlib.compress(content or b''))


def export_content_package(package, backup=False, salt=None, filer=None):
    exporter = component.getAdapter(package,
                                    IInternalObjectExternalizer,
                                    name="exporter")
    externals = {
        'salt': salt,
        'filer': filer,
        'backup': backup
    }
    ext_obj = exporter.toExternalObject(decorate=False,
                                        externals=externals)
    if not backup:
        ext_obj.pop(OID, None)
        for name in (NTIID, INTERNAL_NTIID):
            ntiid = ext_obj.get(name)
            if ntiid:
                ext_obj[name] = hash_ntiid(ntiid, salt)
    for decorator in component.subscribers((package,),
                                           IContentPackageExporterDecorator):
        decorator.decorateExternalObject(package, ext_obj, backup, salt, filer)
    if 'backup' not in ext_obj:
        ext_obj['backup'] = backup
    if 'salt' not in ext_obj:
        ext_obj['salt'] = salt
    return ext_obj
