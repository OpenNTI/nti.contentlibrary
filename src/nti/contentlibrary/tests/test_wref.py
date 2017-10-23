#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_properties

import os

import pickle
from zope import component

from nti.contentlibrary import filesystem
from nti.contentlibrary import interfaces

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentlibrary.wref import ContentUnitWeakRef

from nti.wref.interfaces import IWeakRef

from nti.contentlibrary.tests import ContentlibraryLayerTest


class TestWref(ContentlibraryLayerTest):

    def setUp(self):
        dirname = os.path.dirname(__file__)
        global_library = self.global_library = \
            filesystem.GlobalFilesystemContentPackageLibrary(dirname)

        global_library.syncContentPackages()

        component.getGlobalSiteManager().registerUtility(global_library,
                                                         provided=IContentPackageLibrary)

    def tearDown(self):
        component.getGlobalSiteManager().unregisterUtility(self.global_library,
                                                           provided=IContentPackageLibrary)

    def test_wref(self):
        lib = component.getUtility(interfaces.IContentPackageLibrary)

        ntiid = u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'
        unit = lib[ntiid]

        wref = IWeakRef(unit)
        assert_that(wref, 
                    has_properties('ntiid', is_(ntiid),
                                   '_ntiid', is_(ntiid)))
        assert_that(wref(), is_(unit))

        wref2 = pickle.loads(pickle.dumps(wref))

        assert_that(wref2, is_(wref))
        assert_that(wref2(), is_(unit))

    def test_wref_to_persistent(self):
        unit = filesystem.PersistentFilesystemContentUnit()
        unit.ntiid = u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'

        wref = IWeakRef(unit)
        assert_that(wref, is_(ContentUnitWeakRef))

        # It resolves to what's in the library
        lib = component.getUtility(interfaces.IContentPackageLibrary)

        lib_unit = lib['tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.']

        wref = IWeakRef(unit)
        assert_that(wref(), is_(lib_unit))
