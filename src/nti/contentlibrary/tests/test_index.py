#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

from nti.testing.matchers import is_empty

from nti.contentlibrary.index import LibraryCatalog
from nti.contentlibrary.index import create_library_catalog

from nti.contentlibrary.zodb import RenderableContentPackage

from nti.contentlibrary.tests import ContentlibraryLayerTest


class TestIndex(ContentlibraryLayerTest):

    def test_catalog(self):
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
