#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.contentlibrary import MessageFactory as _

from nti.contentlibrary.interfaces import IContentValidationError

from nti.property.property import alias


@interface.implementer(IContentValidationError)
class ContentValidationError(Exception):

    __external_class_name__ = u"ContentValidationError"

    mime_type = mimeType = u'application/vnd.nextthought.content.validationerror'

    error = alias('Error')

    def __init__(self, error, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.Error = error

class EmptyContentError(ContentValidationError):

    def __init__(self):
        ContentValidationError.__init__(self, _("Empty content"))
