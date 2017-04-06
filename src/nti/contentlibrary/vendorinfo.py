#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component
from zope import interface

from persistent.mapping import PersistentMapping

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageVendorInfo

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject


@component.adapter(IContentPackage)
@interface.implementer(IContentPackageVendorInfo)
class DefaultContentPackageVendorInfo(PersistentMapping,
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
        super(DefaultContentPackageVendorInfo, self).__init__()


@component.adapter(IContentPackage)
@interface.implementer(IContentPackageVendorInfo)
def vendor_info_factory(package):
    try:
        result = package._package_vendor_info
        return result
    except AttributeError:
        result = package._package_vendor_info = DefaultContentPackageVendorInfo()
        result.createdTime = time.time()
        result.__parent__ = package
        result.__name__ = '_package_vendor_info'
        return result
