#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division

__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.contentlibrary.tests import ContentlibraryLayerTest

from nti.contentlibrary.zodb import RenderableContentPackage

class TestRender(ContentlibraryLayerTest):

    def test_render(self):
        # This would need to be in library (with diff ntiid) to
        # test further.
        package = RenderableContentPackage()
        package.ntiid = u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'
        package.title = u'Cohen vs California'
        package.description = u'Cohen vs California'
        package.contentType = b'text/x-rst'
        package.publishLastModified = 10000
        package.write_contents(b'foo', b'text/x-rst')
        package.publish()

