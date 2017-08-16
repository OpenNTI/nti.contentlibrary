#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

from nti.contentlibrary.bucket import AbstractKey

from nti.contentlibrary.interfaces import IContentPackageVendorInfo

from nti.contentlibrary.utils import export_content_package

from nti.contentlibrary.zodb import RenderableContentPackage

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.recorder.adapters import ITransactionRecordHistory

from nti.contentlibrary.tests import ContentlibraryLayerTest


class TestZODB(ContentlibraryLayerTest):

    def test_renderable_io(self):
        package = RenderableContentPackage()
        package.ntiid = u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'
        package.title = u'Cohen vs California'
        package.description = u'Cohen vs California'
        package.contentType = b'text/x-rst'
        package.contents = b'Cohen vs California'
        package.publishLastModified = 10000
        package.index_last_modified = 80000
        ext_obj = export_content_package(package, backup=True)
        assert_that(ext_obj,
                    has_entries('isPublished', is_(False),
                                'publishLastModified', is_(10000),
                                'indexLastModified', is_(80000),
                                'MimeType', 'application/vnd.nextthought.renderablecontentpackage',
                                'NTIID', 'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.',
                                'title', is_('Cohen vs California'),
                                'contents', is_('eJxzzs9IzVMoK1ZwTszJTMsvystMBABEIAcP')))

        factory = find_factory_for(ext_obj)
        assert_that(factory, is_not(none()))
        new_package = factory()
        update_from_external_object(new_package, ext_obj)

        assert_that(new_package,
                    has_property('ntiid', 'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'))
        assert_that(new_package,
                    has_property('title', 'Cohen vs California'))
        assert_that(new_package,
                    has_property('description', 'Cohen vs California'))
        assert_that(new_package,
                    has_property('publishLastModified', is_(10000)))
        assert_that(new_package,
                    has_property('index_last_modified', is_(80000)))
        assert_that(new_package,
                    has_property('contents_key', is_not(none())))
        assert_that(new_package,
                    has_property('contents', is_('Cohen vs California')))
        assert_that(new_package,
                    has_property('contentType', is_('text/x-rst')))

    def test_renderable_contents(self):
        package = RenderableContentPackage()
        package.write_contents(b'foo', b'text/x-rst')
        assert_that(package,
                    has_property('contents', is_(b'foo')))
        assert_that(package,
                    has_property('contentType', is_('text/x-rst')))
        
    def test_icon(self):
        package = RenderableContentPackage()
        package.icon = u'foo'
        package.icon = AbstractKey(name=u'ichigo')
        
    def test_recorder(self):
        package = RenderableContentPackage()
        recorder = ITransactionRecordHistory(package, None)
        assert_that(recorder, is_not(none()))
        assert_that(package, 
                    has_property('_package_trx_record_history', is_(recorder)))
    
    def test_vendorinfo(self):
        package = RenderableContentPackage()
        info = IContentPackageVendorInfo(package, None)
        assert_that(info, is_not(none()))
        assert_that(package, 
                    has_property('_package_vendor_info', is_(info)))
        assert_that(info, validly_provides(IContentPackageVendorInfo))
        assert_that(info, verifiably_provides(IContentPackageVendorInfo))
        assert_that(info, 
                    has_property('__parent__', is_(package)))
