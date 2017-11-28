#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from zope import component
from zope import interface

from zope.annotation.factory import factory as an_factory

from persistent.mapping import PersistentMapping

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageVendorInfo
from nti.contentlibrary.interfaces import IContentPackageBundleVendorInfo

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

logger = __import__('logging').getLogger(__name__)


class DefaultVendorInfo(PersistentMapping,
                        PersistentCreatedAndModifiedTimeObject):
    """
    The default representation of vendor info. We expect the info
    to be small.
    """

    __name__ = None
    __parent__ = None

    # Leave these at 0 until they get set externally
    _SET_CREATED_MODTIME_ON_INIT = False

    def __init__(self):
        super(DefaultVendorInfo, self).__init__()


@component.adapter(IContentPackage)
@interface.implementer(IContentPackageVendorInfo)
class DefaultContentPackageVendorInfo(DefaultVendorInfo):
    pass


@component.adapter(IContentPackage)
@interface.implementer(IContentPackageVendorInfo)
def package_vendor_info_factory(package):
    try:
        result = package._package_vendor_info
        return result
    except AttributeError:
        result = package._package_vendor_info = DefaultContentPackageVendorInfo()
        result.createdTime = time.time()
        result.__parent__ = package
        result.__name__ = u'_package_vendor_info'
        return result


@component.adapter(IContentPackageBundle)
@interface.implementer(IContentPackageBundleVendorInfo)
class DefaultContentPackageBundleVendorInfo(DefaultVendorInfo):
    pass


VENDOR_INFO_KEY = 'ContentPackageBundleVendorInfo'
ContentPackageBundleVendorInfo = an_factory(DefaultContentPackageBundleVendorInfo,
                                            VENDOR_INFO_KEY)
