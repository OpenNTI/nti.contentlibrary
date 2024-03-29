#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

from nti.testing.matchers import is_empty

import os

from zope import component

from nti.contentlibrary.bundle import PersistentContentPackageBundle

from nti.contentlibrary.filesystem import GlobalFilesystemContentPackageLibrary

from nti.contentlibrary.index import LibraryCatalog
from nti.contentlibrary.index import ContentBundleCatalog
from nti.contentlibrary.index import create_library_catalog
from nti.contentlibrary.index import create_contentbundle_catalog

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentlibrary.tests import ContentlibraryLayerTest

from nti.contentlibrary.zodb import RenderableContentPackage


class TestIndex(ContentlibraryLayerTest):

    def setUp(self):
        dirname = os.path.dirname(__file__)
        self.global_library = GlobalFilesystemContentPackageLibrary(dirname)
        self.global_library.syncContentPackages()

        component.getGlobalSiteManager().registerUtility(self.global_library,
                                                         provided=IContentPackageLibrary)

    def tearDown(self):
        component.getGlobalSiteManager().unregisterUtility(self.global_library,
                                                           provided=IContentPackageLibrary)

    def test_library_catalog(self):
        catalog = create_library_catalog()
        assert_that(catalog, is_not(none()))
        assert_that(catalog, has_length(6))
        assert_that(isinstance(catalog, LibraryCatalog), is_(True))

        ntiid = u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'
        package = RenderableContentPackage()
        package.ntiid = ntiid
        package.creator = u'ichigo'
        package.title = u'Cohen vs California'
        package.description = u'Cohen vs California'
        package.publishLastModified = 10000
        package.index_last_modified = 80000
        catalog.index_doc(1, package)

        for query in (
                {'ntiid': {'any_of': (ntiid,)}},
                {'creator': {'any_of': ('ichigo',)}},
                {'mimeType': {'any_of': ('application/vnd.nextthought.renderablecontentpackage',)}}):
            results = catalog.apply(query) or ()
            assert_that(results, is_not(is_empty()))

    def test_bundle_catalog(self):
        catalog = create_contentbundle_catalog()
        assert_that(catalog, is_not(none()))
        assert_that(catalog, has_length(7))
        assert_that(isinstance(catalog, ContentBundleCatalog), is_(True))

        pkg_ntiid = u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'
        package = self.global_library[pkg_ntiid]
        package.ntiid = pkg_ntiid

        ntiid = u'tag:nextthought.com,2011-10:OU-Bundle-JanuxFAQ'
        bundle = PersistentContentPackageBundle()
        bundle.ntiid = ntiid
        bundle.creator = u'ichigo'
        bundle.title = u'Janux FAQ'
        bundle.ContentPackages = (package,)
        catalog.index_doc(1, bundle)

        for query in (
                {'ntiid': {'any_of': (ntiid,)}},
                {'creator': {'any_of': ('ichigo',)}},
                {'title': {'any_of': ('Janux FAQ',)}},
                {'packages': {'any_of': (pkg_ntiid,)}},
                {'restrictedAccess': {'any_of': (False,)}},
                {'mimeType': {'any_of': ('application/vnd.nextthought.contentpackagebundle',)}}):
            results = catalog.apply(query) or ()
            assert_that(results, is_not(is_empty()))
