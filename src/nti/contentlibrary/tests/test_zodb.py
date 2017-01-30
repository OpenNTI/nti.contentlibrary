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
from hamcrest import has_property

from nti.contentlibrary.zodb import RenderableContentPackage

from nti.externalization.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.contentlibrary.tests import ContentlibraryLayerTest


class TestZODB(ContentlibraryLayerTest):

    def test_renderable_io(self):
        package = RenderableContentPackage()
        package.ntiid = u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'
        package.title = u'Cohen vs California'
        package.description = u'Cohen vs California'
        package.contentType = b'text/x-rst'
        package.publishLastModified = 10000
        ext_obj = to_external_object(package, name='exporter')
        assert_that(ext_obj,
                    has_entries(u'isPublished', is_(False),
                                u'publishLastModified', is_(10000),
                                u'MimeType', 'application/vnd.nextthought.renderablecontentpackage',
                                u'NTIID', u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.',
                                u'title', is_(u'Cohen vs California')))

        factory = find_factory_for(ext_obj)
        assert_that(factory, is_not(none()))
        new_package = factory()
        update_from_external_object(new_package, ext_obj)

        assert_that(new_package,
                    has_property('ntiid', u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'))
        assert_that(new_package,
                    has_property('title', u'Cohen vs California'))
        assert_that(new_package,
                    has_property('description', u'Cohen vs California'))
        assert_that(new_package,
                    has_property('publishLastModified', is_(10000)))
        assert_that(new_package,
                    has_property('contents_key', is_not(none())))

    def test_renderable_contents(self):
        package = RenderableContentPackage()
        package.write_contents(b'foo', b'text/x-rst')
        assert_that(package,
                    has_property('contents', is_(b'foo')))
        assert_that(package,
                    has_property('contentType', is_('text/x-rst')))
