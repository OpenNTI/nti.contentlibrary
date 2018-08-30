#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Weak references for content units.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from functools import total_ordering

from zope import component
from zope import interface

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.ntiids.ntiids import validate_ntiid_string

from nti.property.property import alias

from nti.schema.eqhash import EqHash

from nti.wref.interfaces import IWeakRef

logger = __import__('logging').getLogger(__name__)


@total_ordering
@EqHash('_ntiid')
@component.adapter(IContentUnit)
@interface.implementer(IWeakRef)
class ContentUnitWeakRef(object):

    __slots__ = ('_ntiid',)

    ntiid = alias('_ntiid')

    def __init__(self, contentunit):
        self._ntiid = contentunit.ntiid
        validate_ntiid_string(self._ntiid)

    def __call__(self):
        # We're not a caching weak ref, we need to pick
        # up on changes that happen in the library
        lib = component.queryUtility(IContentPackageLibrary)
        if lib is not None:
            return lib.get(self._ntiid)
        return None

    def __lt__(self, other):
        try:
            return self.ntiid < other.ntiid
        except AttributeError:
            return NotImplemented

    def __gt__(self, other):
        try:
            return self.ntiid > other.ntiid
        except AttributeError:
            return NotImplemented

    def __getstate__(self):
        return (1, self._ntiid)

    def __setstate__(self, state):
        assert state[0] == 1
        self._ntiid = state[1]

    def __str__(self):
        return self._ntiid

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           self._ntiid)


def contentunit_wref_to_missing_ntiid(ntiid):
    """
    If you have an NTIID, and have no library to look it up
    in, or the library lookup failed, but you expect
    the NTIID to appear in the library in the future, you
    may use this function. Simply pass in a valid
    content ntiid, and a weak ref will be returned
    which you can attempt to resolve in the future.
    """

    validate_ntiid_string(ntiid)
    wref = ContentUnitWeakRef.__new__(ContentUnitWeakRef)
    wref._ntiid = ntiid  # pylint: disable=protected-access
    return wref
