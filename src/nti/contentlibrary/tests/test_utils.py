#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

import os
import shutil
import tempfile

from nti.contentlibrary.utils import create_display_resources
from nti.contentlibrary.utils import is_valid_presentation_assets_source

from nti.contentlibrary.tests import ContentlibraryLayerTest


class TestUtils(ContentlibraryLayerTest):

    def test_is_valid_presentation_asset_source(self):
        path = os.path.join(os.path.dirname(__file__),
                            'TestFilesystem',
                            'presentation-assets')
        result = is_valid_presentation_assets_source(path)
        assert_that(result, is_(path))

        tmpdir = tempfile.mkdtemp()
        try:
            filename = os.path.join(tmpdir, "source")
            filename = shutil.make_archive(filename, 'zip', path)
            result = is_valid_presentation_assets_source(filename)
            assert_that(result, is_not(path))
            assert_that(os.path.isdir(result), is_(True))
            shutil.rmtree(result, ignore_errors=True)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        result = is_valid_presentation_assets_source(os.path.dirname(__file__))
        assert_that(result, is_(False))
        
        result = is_valid_presentation_assets_source(None)
        assert_that(result, is_(False))

    def test_create_display_resources_from_disk(self):
        path = os.path.join(os.path.dirname(__file__),
                            'TestFilesystem')
        resources = create_display_resources(path)
        assert_that(resources, has_length(3))
