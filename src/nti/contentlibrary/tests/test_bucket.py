#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_key
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import is_not as does_not

import os
import pickle
import shutil
import tempfile
import unittest

from nti.contentlibrary import DELETED_MARKER

from nti.contentlibrary.bucket import AbstractKey

from nti.contentlibrary.filesystem import FilesystemBucket

from nti.contentlibrary.interfaces import IDelimitedHierarchyKey


class TestBucket(unittest.TestCase):

    def test_no_volatile_attrs(self):
        key = AbstractKey()
        key._v_test = 1
        key.a = 42

        s = pickle.dumps(key)

        key2 = pickle.loads(s)

        assert_that(key2.__dict__,
                    does_not(has_key('_v_test')))
        assert_that(key2, has_property('a', 42))

        key2.__setstate__({'_v_test': 1})

        assert_that(key2.__dict__,
                    does_not(has_key('_v_test')))

    def test_deleted_marker(self):
        tmpdir = tempfile.mkdtemp()
        try:
            bucket = FilesystemBucket(name=u"test")
            bucket.absolute_path = tmpdir
            marker = os.path.join(tmpdir, DELETED_MARKER)
            with open(marker, "wb") as fp:
                fp.write(b'')
            key = bucket.getChildNamed(DELETED_MARKER)
            assert_that(IDelimitedHierarchyKey.providedBy(key),
                        is_(True))
        finally:
            shutil.rmtree(tmpdir)
