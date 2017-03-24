#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adopter implementations.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component
from zope import interface

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.recorder.interfaces import ITransactionRecordHistory

from nti.recorder.adapters import TransactionRecordContainer


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
        return result
    except AttributeError:
        result = package._package_trx_record_history = TransactionRecordContainer()
        result.createdTime = time.time()
        result.__parent__ = package
        result.__name__ = '_package_trx_history'
        return result
