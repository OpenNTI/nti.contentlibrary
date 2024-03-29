#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

#: NTI Provider
NTI = u'NTI'

#: Content package NTIID Type
HTML = u'HTML'

#: Content package bundle NTIID Type
BUNDLE = u'Bundle'

#: Named prefix to distinguish API created content
AUTHORED_PREFIX = u"_authored"

#: Deleted directory marker
DELETED_MARKER = u"__nti_deleted_marker__"

#: Named prefix to distinguish API rendered content
RENDERED_PREFIX = u"_rendered"

#: reStructuredText mime type
RST_MIMETYPE = b'text/x-rst'

#: Content vendor info file name
VENDOR_INFO_NAME = 'vendor_info.json'

#: Content package bundle bucket name
CONTENT_PACKAGE_BUNDLES = 'ContentPackageBundles'

CONTENT_UNIT_MIME_TYPE = 'application/vnd.nextthought.contentunit'
CONTENT_PACKAGE_MIME_TYPE = 'application/vnd.nextthought.contentpackage'

PERSISTENT_CONTENT_UNIT_MIME_TYPE = 'application/vnd.nextthought.persistentcontentunit'
PERSISTENT_CONTENT_PACKAGE_MIME_TYPE = 'application/vnd.nextthought.persistentcontentpackage'

RENDERABLE_CONTENT_UNIT_MIME_TYPE = 'application/vnd.nextthought.renderablecontentunit'
RENDERABLE_CONTENT_PACKAGE_MIME_TYPE = 'application/vnd.nextthought.renderablecontentpackage'

LEGACY_CONTENT_MIME_TYPES = (CONTENT_UNIT_MIME_TYPE,
                             CONTENT_PACKAGE_MIME_TYPE)

RENDERABLE_CONTENT_MIME_TYPES = (RENDERABLE_CONTENT_UNIT_MIME_TYPE,
                                 RENDERABLE_CONTENT_PACKAGE_MIME_TYPE)

ALL_CONTENT_MIMETYPES = (CONTENT_UNIT_MIME_TYPE,
                         CONTENT_PACKAGE_MIME_TYPE,
                         RENDERABLE_CONTENT_UNIT_MIME_TYPE,
                         RENDERABLE_CONTENT_PACKAGE_MIME_TYPE,
                         PERSISTENT_CONTENT_UNIT_MIME_TYPE,
                         PERSISTENT_CONTENT_PACKAGE_MIME_TYPE)

ALL_CONTENT_PACKAGE_MIME_TYPES = (CONTENT_PACKAGE_MIME_TYPE,
                                  PERSISTENT_CONTENT_PACKAGE_MIME_TYPE,
                                  RENDERABLE_CONTENT_PACKAGE_MIME_TYPE)

from nti.contentlibrary.index import get_contentlibrary_catalog

from nti.contentlibrary.synchronize import ContentRemovalException
from nti.contentlibrary.synchronize import DuplicatePacakgeException
from nti.contentlibrary.synchronize import MissingContentBundleNTIIDException
from nti.contentlibrary.synchronize import MissingContentPacakgeReferenceException
