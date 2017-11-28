#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import copy
import time

from zope import component
from zope import lifecycleevent

from zope.cachedescriptors.property import readproperty

from nti.base._compat import text_
from nti.base._compat import bytes_

from nti.contentlibrary import RST_MIMETYPE

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IContentPackageImporterUpdater

from nti.contentlibrary.library import add_to_connection
from nti.contentlibrary.library import register_content_units

from nti.contentlibrary.utils import make_content_package_ntiid

from nti.contentlibrary.validators import ContentValidationError
from nti.contentlibrary.validators import validate_content_package

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.externalization.proxy import removeAllProxies

from nti.intid.common import addIntId

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.recorder.interfaces import TRX_TYPE_IMPORT

from nti.recorder.utils import record_transaction

logger = __import__('logging').getLogger(__name__)


def copy_attributes(source, target, names):
    for name in names or ():
        value = getattr(source, name, None)
        if value is not None:
            setattr(target, name, value)


class ContentPackageImporterMixin(object):

    DEFAULT_MIME_TYPE = RST_MIMETYPE

    @readproperty
    def library(self):
        return component.getUtility(IContentPackageLibrary)

    def get_ntiid(self, obj):
        return getattr(obj, 'ntiid', None)

    def is_new(self, obj, unused_course=None):
        result = None
        ntiid = self.get_ntiid(obj)
        if ntiid:
            result = find_object_with_ntiid(ntiid)
        return removeAllProxies(result) if result is not None else None

    def validate_content_package(self, package):
        error = validate_content_package(package)
        if error is not None:
            e, unused = error
            raise e

    def handle_package(self, the_object, source, context=None, **kwargs):
        result = the_object
        stored = self.is_new(the_object)
        if stored is not None:
            if stored is not result:  # replace
                result = stored
                assert IEditableContentPackage.providedBy(result)
                # copy all new content package attributes
                copy_attributes(the_object, result, IContentPackage.names())
                # copy content unit attributes
                attributes = set(IContentUnit.names()) - {'children', 'ntiid'}
                copy_attributes(the_object, result, attributes)
                # copy contents
                result.contents = the_object.contents
                result.contentType = the_object.contentType or self.DEFAULT_MIME_TYPE
            else:
                for key in ('contents', 'contentType'):
                    if source.get(key):
                        setattr(result, key, bytes_(source.get(key)))
                for key in ('title', 'description'):
                    if source.get(key):
                        setattr(result, key, text_(source.get(key)))
            # record trx
            result.contents_last_modified = time.time()
            record_transaction(result, type_=TRX_TYPE_IMPORT,
                               ext_value={
                                   u'contents': result.contents,
                                   u'contentType': result.contentType,
                                   u'version': text_(result.contents_last_modified)
                               })
        else:
            if context is None:
                context = component.getSiteManager()
            # Use whatever NTIID we have...
            ntiid = self.get_ntiid(result)
            if ntiid is None:
                add_to_connection(context, result)
                addIntId(result)  # gain an intid
                result.ntiid = make_content_package_ntiid(result)
            register_content_units(context, result)
            # we need events to update
            self.library.add(result, event=True)

        is_published = source.get('isPublished')
        if is_published:
            try:
                self.validate_content_package(result)
                result.publish()  # event trigger render job
            except ContentValidationError:
                # Nothing we can do about this except log.
                logger.warn('Invalid content in published package (%s)',
                            result.ntiid,
                            exc_info=True)

        locked = source.get('isLocked')
        if locked:
            result.lock(event=False)
        # update from subscribers
        for updater in component.subscribers((result,),
                                             IContentPackageImporterUpdater):
            updater.updateFromExternalObject(result, source, **kwargs)
        # update indexes
        lifecycleevent.modified(result)
        return result, (stored is None)

    def handle_packages(self, items, context=None, **kwargs):
        added = []
        modified = []
        for ext_obj in items or ():
            source = copy.deepcopy(ext_obj)
            factory = find_factory_for(ext_obj)
            the_object = factory()  # create object
            assert IEditableContentPackage.providedBy(the_object)
            update_from_external_object(the_object, ext_obj, notify=False)
            package, is_new = self.handle_package(the_object, source, 
                                                  context, **kwargs)
            if is_new:
                added.append(package)
            else:
                modified.append(package)
        return added, modified
