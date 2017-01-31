#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import raises
from hamcrest import calling
from hamcrest import assert_that
from hamcrest import greater_than
from hamcrest import has_property
from nti.testing.matchers import verifiably_provides

import os

from zope import component

from nti.contentlibrary.filesystem import FilesystemBucket
from nti.contentlibrary.filesystem import GlobalFilesystemContentPackageLibrary

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IEditableContentPackageBundle

from nti.contentlibrary import MissingContentPacakgeReferenceException

from nti.contentlibrary.bundle import _ContentBundleMetaInfo
from nti.contentlibrary.bundle import sync_bundle_from_json_key
from nti.contentlibrary.bundle import PersistentContentPackageBundle

from nti.contentlibrary.tests import ContentlibraryLayerTest

from nti.testing.time import time_monotonically_increases


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
    
    @time_monotonically_increases
    def test_sync_bundle_from_meta(self):
        bucket = FilesystemBucket()
        bucket.absolute_path = os.path.join(os.path.dirname(__file__),
                                            'sites', 'localsite',
                                            'ContentPackageBundles', 'ABundle')
        bucket.name = 'ABundle'
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
        del meta._ContentPackages_wrefs
        sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
        assert_that(bundle, has_property('lastModified', greater_than(lm)))
        lm = bundle.lastModified

        # adding them back
        sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
        assert_that(bundle, has_property('lastModified', greater_than(lm)))

    @time_monotonically_increases
    def test_missing_package(self):
        bucket = FilesystemBucket()
        bucket.absolute_path = os.path.join(os.path.dirname(__file__),
                                            'sites', 'localsite',
                                            'ContentPackageBundles', 'ABundle')
        bucket.name = 'ABundle'
        key = bucket.getChildNamed('bundle_meta_info.json')

        bundle = PersistentContentPackageBundle()
        bundle.lastModified = -1
        bundle.createdTime = -1

        meta = _ContentBundleMetaInfo(key, self.global_library)
        meta.lastModified = -1

        sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)

        # Empty our library
        self.global_library._contentPackages = {}
        self.global_library._contentPackagesByNtiid = {}
        # We will raise if the package is missing
        assert_that(calling(sync_bundle_from_json_key).with_args(key, 
                                                                 bundle,
                                                                 self.global_library, 
                                                                 _meta=meta),
                    raises(MissingContentPacakgeReferenceException))
