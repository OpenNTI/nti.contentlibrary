#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for defining and traversing libraries composed of
independent (but possibly related and/or linked) units of content.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

#: Content package NTIID Type
HTML = u'HTML'

#: Named prefix to distinguish API created content
AUTHORED_PREFIX = "_authored"

CONTENT_UNIT_MIME_TYPE = u'application/vnd.nextthought.contentunit'
CONTENT_PACKAGE_MIME_TYPE = u'application/vnd.nextthought.contentpackage'

PERSISTENT_CONTENT_UNIT_MIME_TYPE = u'application/vnd.nextthought.persistentcontentunit'
PERSISTENT_CONTENT_PACKAGE_MIME_TYPE = u'application/vnd.nextthought.persistentcontentpackage'

RENDERABLE_CONTENT_UNIT_MIME_TYPE = u'application/vnd.nextthought.renderablecontentunit'
RENDERABLE_CONTENT_PACKAGE_MIME_TYPE = u'application/vnd.nextthought.renderablecontentpackage'

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
