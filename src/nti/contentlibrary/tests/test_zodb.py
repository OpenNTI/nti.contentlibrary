#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_entries

from nti.contentlibrary.zodb import RenderableContentPackage

from nti.externalization.externalization import to_external_object

from nti.contentlibrary.tests import ContentlibraryLayerTest


class TestZODB(ContentlibraryLayerTest):

    def test_renderable(self):
        package = RenderableContentPackage()
        package.ntiid = u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'
        package.title = u'Cohen vs California'
        package.description = u'Cohen vs California'
        package.publishLastModified = 0
        ext_obj = to_external_object(package)
        assert_that(ext_obj,
                    has_entries(u'publishLastModified', is_not(none()),
								u'NTIID', is_(u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'),
								u'title', is_(u'Cohen vs California')))
