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
from hamcrest import has_entries
from hamcrest import greater_than
from hamcrest import has_property

from nti.testing.matchers import verifiably_provides

from nti.testing.time import time_monotonically_increases

import os

from zope import component

from nti.contentlibrary.filesystem import FilesystemBucket
from nti.contentlibrary.filesystem import GlobalFilesystemContentPackageLibrary

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IEditableContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageBundleVendorInfo

from nti.contentlibrary.bundle import _ContentBundleMetaInfo
from nti.contentlibrary.bundle import sync_bundle_from_json_key
from nti.contentlibrary.bundle import PersistentContentPackageBundle

from nti.externalization.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.contentlibrary.tests import ContentlibraryLayerTest


class TestBundle(ContentlibraryLayerTest):

    def setUp(self):
        path = os.path.dirname(__file__)
        global_library = self.global_library = GlobalFilesystemContentPackageLibrary(path)
        global_library.syncContentPackages()
        component.getGlobalSiteManager().registerUtility(global_library,
                                                         provided=IContentPackageLibrary)

    def tearDown(self):
        component.getGlobalSiteManager().unregisterUtility(self.global_library,
                                                           provided=IContentPackageLibrary)

    @time_monotonically_increases
    def test_bundle(self):
        bundle = PersistentContentPackageBundle()
        assert_that(bundle, verifiably_provides(IEditableContentPackageBundle))
        vendor = IContentPackageBundleVendorInfo(bundle, None)
        assert_that(vendor, is_not(none()))
        assert_that(vendor, verifiably_provides(IContentPackageBundleVendorInfo))
        assert_that(vendor,
                    has_property('__parent__', is_(bundle)))

    @time_monotonically_increases
    def test_sync_bundle_from_meta(self):
        bucket = FilesystemBucket()
        bucket.absolute_path = os.path.join(os.path.dirname(__file__),
                                            'sites', 'localsite',
                                            'ContentPackageBundles', 'ABundle')
        bucket.name = u'ABundle'
        key = bucket.getChildNamed('bundle_meta_info.json')

        bundle = PersistentContentPackageBundle()
        bundle.lastModified = -1
        bundle.createdTime = -1

        meta = _ContentBundleMetaInfo(key, self.global_library)
        meta.lastModified = -1

        sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
        lm = bundle.lastModified

        # Nothing should change now
        sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
        assert_that(bundle, has_property('lastModified', lm))

        # removing packages
        empty_meta = _ContentBundleMetaInfo(key, self.global_library)
        empty_meta.lastModified = -1
        del empty_meta._ContentPackages_wrefs
        sync_bundle_from_json_key(key, bundle, self.global_library, _meta=empty_meta)
        assert_that(bundle, has_property('lastModified', greater_than(lm)))
        lm = bundle.lastModified

        # adding them back
        sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
        assert_that(bundle, has_property('lastModified', greater_than(lm)))

        ext_obj = to_external_object(bundle)
        assert_that(ext_obj,
                    has_entries('Class', 'ContentPackageBundle',
                                'ContentPackages', has_length(1),
                                'MimeType', 'application/vnd.nextthought.contentpackagebundle',
                                'NTIID', 'tag:nextthought.com,2011-10:NTI-Bundle-ABundle',
                                'title', 'A Title',
                                'root', '/ABundle/',
                                'PlatformPresentationResources', has_length(3)))

        ext_obj['ContentPackages'] = [u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.']
        factory = find_factory_for(ext_obj)
        assert_that(factory, is_not(none()))

        bundle = factory()
        update_from_external_object(bundle, ext_obj, notify=False)
        assert_that(bundle,
                    has_property('ntiid', 'tag:nextthought.com,2011-10:NTI-Bundle-ABundle'))
        assert_that(bundle,
                    has_property('title', 'A Title'))
        assert_that(bundle,
                    has_property('ContentPackages', has_length(1)))

        # Validate restricted access
        bucket = FilesystemBucket()
        bucket.absolute_path = os.path.join(os.path.dirname(__file__),
                                            'sites', 'localsite',
                                            'ContentPackageBundles', 'RestrictedBundle')
        bucket.name = u'RestrictedBundle'
        key = bucket.getChildNamed('bundle_meta_info.json')
        bundle = PersistentContentPackageBundle()
        bundle.lastModified = -1
        bundle.createdTime = -1
        meta = _ContentBundleMetaInfo(key, self.global_library)
        meta.lastModified = -1
        sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
        assert_that(bundle, has_property('RestrictedAccess', is_(True)))


    @time_monotonically_increases
    def test_missing_package(self):
        bucket = FilesystemBucket()
        bucket.absolute_path = os.path.join(os.path.dirname(__file__),
                                            'sites', 'localsite',
                                            'ContentPackageBundles', 'ABundle')
        bucket.name = u'ABundle'
        key = bucket.getChildNamed('bundle_meta_info.json')

        bundle = PersistentContentPackageBundle()
        bundle.lastModified = -1
        bundle.createdTime = -1

        meta = _ContentBundleMetaInfo(key, self.global_library)
        meta.lastModified = -1

        sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
