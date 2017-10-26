#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapter implementations.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from zope import component
from zope import interface

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.recorder.interfaces import ITransactionManager
from nti.recorder.interfaces import ITransactionRecordHistory

from nti.recorder.adapters import DefaultTransactionManager
from nti.recorder.adapters import TransactionRecordContainer

from nti.site.interfaces import IHostPolicyFolder

from nti.traversal.traversal import find_interface

logger = __import__('logging').getLogger(__name__)


@component.adapter(IContentUnit)
@interface.implementer(IHostPolicyFolder)
def contentunit_to_site(context):
    return find_interface(context, IHostPolicyFolder, strict=False)


@component.adapter(IContentPackageBundle)
@interface.implementer(IHostPolicyFolder)
def contentbundle_to_site(context):
    return find_interface(context, IHostPolicyFolder, strict=False)


@component.adapter(IContentPackageLibrary)
@interface.implementer(IDelimitedHierarchyContentPackageEnumeration)
def enumeration_from_library(library):
    """
    Provide the library's enumeration.

    .. warning:: This relies on an implementation detail, the fact
            that all libraries we currently have use a library
            with this interface. This may break in the future,
            in which case this adapter will raise an exception.
    """
    e = library._enumeration  # pylint: disable=I0011,W0212
    assert IDelimitedHierarchyContentPackageEnumeration.providedBy(e)
    return e


@component.adapter(IEditableContentPackage)
@interface.implementer(ITransactionRecordHistory)
def trx_recorder_history_factory(package):
    try:
        result = package._package_trx_record_history
    except AttributeError:
        result = package._package_trx_record_history = TransactionRecordContainer()
        result.createdTime = time.time()
        result.__parent__ = package
        result.__name__ = u'_package_trx_record_history'
    return result


@component.adapter(IEditableContentPackage)
@interface.implementer(ITransactionManager)
class ContentPackageTransactionManager(DefaultTransactionManager):

    def has_transactions(self):
        try:
            result = self.context._package_trx_record_history
            return bool(result)
        except AttributeError:
            return False
