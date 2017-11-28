#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os.path
import functools

import boto

from zope import interface

from zope.component import getSiteManager

from zope.component.zcml import utility

from zope.configuration.exceptions import ConfigurationError

import zope.configuration.fields

from nti.base._compat import text_

from nti.contentlibrary.boto_s3 import NameEqualityBucket
from nti.contentlibrary.boto_s3 import BotoS3BucketContentLibrary

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.filesystem import GlobalFilesystemContentPackageLibrary

from nti.contentlibrary.externalization import map_all_buckets_to

from nti.schema.field import ValidTextLine

logger = __import__('logging').getLogger(__name__)


class IFilesystemLibrary(interface.Interface):
    """
    Register a content library read from the filesystem.
    """

    directory = zope.configuration.fields.Path(
        title=u"Path to a directory containing content as subdirectories.",
        required=True
    )

    prefix = ValidTextLine(
        title=u"The URL prefix for the content items",
        description=u"""If you do not give this, then the content items are assumed to be directly
            accessible from the root of the URL space. This is most commonly needed
            when setting up multiple libraries for different sub-sites; in that case each
            such library must use a different prefix.

            If Pyramid will be serving the content files (NOT for production usage), then the prefix
            is arbitrary. If Apache/nginx will be serving the content files, then the prefix
            must match what they will be serving the content files at; often this will be the name
            of the directory.
            """,
        required=False,
        default=u"")


def registerFilesystemLibrary(_context, directory=None, prefix=""):
    if not directory or not os.path.isdir(directory):
        raise ConfigurationError("Must give the path of a readable directory")

    # Normalize prefix if needed
    if prefix and not prefix.startswith('/'):
        prefix = '/' + prefix
    if prefix and not prefix.endswith('/'):
        prefix = prefix + '/'

    factory = functools.partial(GlobalFilesystemContentPackageLibrary,
                                root=text_(directory),
                                prefix=text_(prefix))
    utility(_context, factory=factory, provides=IContentPackageLibrary)
register_filesystem_library = registerFilesystemLibrary


class IS3Library(interface.Interface):
    """
    Register a library pulled from an S3 bucket.
    """

    bucket = ValidTextLine(
        title=u"The name of the S3 bucket that contains content",
        description=u"For example, dev-content.nextthought.com",
        required=True
    )

    cdn_name = ValidTextLine(
        title=u"The name of a CDN distribution placed on top of the S3 bucket.",
        description=u"For example, d2wnvtui8zrua9.cloudfront.net",
        required=False
    )


def registerS3Library(_context, bucket, cdn_name=None):

    def _connect_and_register(bucket, info):
        conn = boto.connect_s3()
        # CAUTION: See warning in this class
        conn.bucket_class = NameEqualityBucket
        boto_bucket = conn.get_bucket(bucket)
        library = BotoS3BucketContentLibrary(boto_bucket)
        getSiteManager().registerUtility(library,
                                         provided=IContentPackageLibrary,
                                         info=info)

    # Use the same discriminator as normally registering a utility
    # does. That way, we properly conflict with a filesystem library
    _context.action(
        discriminator=('utility', IContentPackageLibrary, u''),
        callable=_connect_and_register,
        args=(text_(bucket), _context.info),
    )
    # If we are serving content from a bucket, we might have a CDN on top of it
    # in the case that we are also serving the application. Rewrite bucket
    # rules with that in mind, replacing the HTTP Host: and Origin: aware stuff
    # we would do if we were serving the application and content both from a
    # cdn.
    if cdn_name:
        cdn_name = text_(cdn_name)
        _context.action(
            discriminator=('map_all_buckets_to', cdn_name),
            callable=map_all_buckets_to,
            args=(cdn_name,),
            kw={'_global': False}
        )
register_s3_library = registerS3Library
