#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys

from zope import component
from zope import interface

from nti.contentlibrary import MessageFactory as _

from nti.contentlibrary.interfaces import IContentValidator
from nti.contentlibrary.interfaces import IContentValidationError


@interface.implementer(IContentValidationError)
class ContentValidationError(Exception):

    __external_class_name__ = u"ContentValidationError"

    mime_type = mimeType = u'application/vnd.nextthought.content.validationerror'

    def __init__(self, message, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.message = message


class EmptyContentError(ContentValidationError):

    def __init__(self):
        ContentValidationError.__init__(self, _("Empty content"))


def validate_content_package(package):
    """
    Validate the contents of the specified package
    """
    content_type = package.contentType
    validator = component.queryUtility(IContentValidator,
                                       name=content_type)
    if validator is not None:
        try:
            contents = package.contents
            validator.validate(contents)
        except Exception as e:
            exc_info = sys.exc_info()
            return e, exc_info
