#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904,E1121

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import greater_than_or_equal_to

from nti.testing.matchers import validly_provides

import six
import fudge

from zope import interface

from zope.site.folder import Folder
from zope.site.folder import rootFolder

from nti.contentlibrary import boto_s3
from nti.contentlibrary import filesystem
from nti.contentlibrary import interfaces

from nti.contentlibrary.tests import ContentlibraryLayerTest

from nti.externalization.interfaces import IExternalObject


class TestExternalization(ContentlibraryLayerTest):

    def test_doesnt_dual_escape(self):
        bucket = filesystem.FilesystemBucket(name=u"prealgebra",
                                             bucket=rootFolder())
        bucket.__parent__.absolute_path = u'/'
        key = filesystem.FilesystemKey(bucket=bucket,
                                       name=u'index.html')
        unit = filesystem.FilesystemContentPackage(
            key=key,
            # filename='prealgebra/index.html',
            href=u'index.html',
            # root='prealgebra'
        )

        unit.icon = unit.make_sibling_key(u'icons/The%20Icon.png')
        assert_that(unit.icon,
                    validly_provides(interfaces.IDelimitedHierarchyKey))

        assert_that(IExternalObject(unit).toExternalObject(),
                    has_entry('icon', '/prealgebra/icons/The%20Icon.png'))

    def _do_test_escape_if_needed(self, factory, key,
                                  index=u'eclipse-toc.xml',
                                  archive_unit=None,
                                  prefix=u'',
                                  installable=True):
        if isinstance(key, six.string_types):
            parts = key.split('/')
            parent = rootFolder()
            parent.absolute_path = '/'
            if parts and parts[0] == '':
                parts = parts[1:]
            for k in parts[:-1]:
                parent = filesystem.FilesystemBucket(bucket=parent, name=k)
            key = filesystem.FilesystemKey(bucket=parent, name=parts[-1])

        unit = factory(key=key,
                       href=u'index.html',
                       # root='prealgebra',
                       title=u'Prealgebra',
                       description=u'',
                       installable=installable,
                       index=index,
                       isCourse=True)
        unit.icon = unit.make_sibling_key(u'icons/The Icon.png')

        # This is a legacy code path for boto, which is not yet updated
        if archive_unit:
            print(unit)
            unit.archive_unit = archive_unit
            unit.archive_unit.__parent__ = unit
            if not archive_unit.key.__parent__:
                unit.archive_unit.key.__parent__ = filesystem.FilesystemBucket(name=u'prealgebra',
                                                                               bucket=unit)

        interface.alsoProvides(unit,
                               interfaces.ILegacyCourseConflatedContentPackage)
        result = IExternalObject(unit).toExternalObject()
        assert_that(result,
                    has_entry('icon',
                              prefix + '/prealgebra/icons/The%20Icon.png'))

        assert_that(result, has_key('index_jsonp'))
        assert_that(result, has_entry('renderVersion', 1))
        assert_that(result, has_entry('isCourse', True))
        assert_that(result, has_entry('Class', 'ContentPackage'))
        # Not when isCourse is false
        # assert_that(result, has_entry('courseName', is_(none())))
        # assert_that(result, has_entry('courseTitle', is_(none())))

        # More coverage
        assert_that(result,
                    has_entries('DCCreator', (),
                                'DCTitle', 'Prealgebra',
                                'Last Modified', greater_than_or_equal_to(-1),
                                'index', prefix +
                                '/prealgebra/eclipse-toc.xml',
                                'root', prefix + '/prealgebra/',
                                'archive', prefix + '/prealgebra/archive.zip',
                                'installable', installable))
        return unit

    def test_escape_if_needed_filesystem_rel_path(self):
        def factory(**kwargs):
            r = filesystem.FilesystemContentPackage(**kwargs)
            r.index = r.make_sibling_key(u'eclipse-toc.xml')
            if 'archive_unit' not in kwargs or not kwargs['archive_unit']:
                r.archive_unit = filesystem.FilesystemContentUnit(key=r.make_sibling_key(u'archive.zip'),
                                                                  href=u'archive.zip')

            return r
        self._do_test_escape_if_needed(factory,
                                       key=u'prealgebra/index.html',
                                       index=None)

    def test_escape_if_needed_filesystem_full_path(self):

        def factory(**kwargs):
            r = filesystem.FilesystemContentPackage(**kwargs)
            r.archive_unit = filesystem.FilesystemContentUnit(key=r.make_sibling_key(u'archive.zip'),
                                                              href=u'archive.zip')
            r.index = r.make_sibling_key(u'eclipse-toc.xml')
            return r

        root = rootFolder()
        root.absolute_path = u'/'
        # Do not fire events
        child = Folder()
        root.__setitem__(u'DNE', child)

        new_child = Folder()
        child.__setitem__(u'Library', new_child)
        child = new_child

        new_child = Folder()
        child.__setitem__(u'WebServer', new_child)
        child = new_child

        new_child = Folder()
        child.__setitem__(u'Documents', new_child)
        child = new_child
        child.url_prefix = ''
        child.absolute_path = u'/DNE/Library/WebServer/Documents'

        bucket = filesystem.FilesystemBucket(name=u"prealgebra", bucket=child)
        key = filesystem.FilesystemKey(bucket=bucket, name=u'index.html')

        package = self._do_test_escape_if_needed(factory,
                                                 index=None,
                                                 key=key,
                                                 installable=True)

        # If we have escaped spaces encoded and quoted and a fragment, we make it through
        # the original href is encoded...
        child_href_with_spaces = u'Sample_2_chFixedinc.html#SecPOjjaf%20copy%282%29'
        # a href-to-pathname transformation is done...
        from nti.contentlibrary.eclipse import _href_for_sibling_key
        child_name_with_spaces = _href_for_sibling_key(child_href_with_spaces)
        assert_that(child_name_with_spaces,
                    is_('Sample_2_chFixedinc.html'))
        # ...finally producing the key
        child_key_with_spaces = package.make_sibling_key(
            child_name_with_spaces)
        assert_that(child_key_with_spaces.name,
                    is_('Sample_2_chFixedinc.html'))

        child = filesystem.FilesystemContentUnit(key=child_key_with_spaces,
                                                 href=child_href_with_spaces)

        # and we reproduce the original href
        mapper = interfaces.IContentUnitHrefMapper(child)
        assert_that(mapper,
                    has_property('href',
                                 '/prealgebra/' + child_href_with_spaces))

    @fudge.patch('nti.contentlibrary.boto_s3.BotoS3ContentUnit._connect_key')
    def test_escape_if_needed_boto(self, fake_connect):
        fake_connect.expects_call()
        bucket = boto_s3.NameEqualityBucket(name=u'content.nextthought.com')
        key = bucket.key_class(bucket=bucket, name=u'prealgebra/index.html')
        key.last_modified = 0
        index = bucket.key_class(bucket=bucket,
                                 name=u'prealgebra/eclipse-toc.xml')

        assert_that(key, is_not(index))
        assert_that(key, is_(key))
        assert_that(bucket, is_(bucket))
        d = {key: index}
        key2 = bucket.key_class(bucket=bucket,
                                name=u'prealgebra/index.html')
        assert_that(d.get(key2), is_(index))

        self._do_test_escape_if_needed(
            boto_s3.BotoS3ContentPackage,
            key=key,
            index=index,
            prefix=u'http://content.nextthought.com',
            archive_unit=boto_s3.BotoS3ContentUnit(key=boto_s3.NameEqualityKey(bucket=bucket,
                                                                               name=u'prealgebra/archive.zip')),
            installable=True)
