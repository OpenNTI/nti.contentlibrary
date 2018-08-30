#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import sys

from zope import component
from zope import interface

from nti.contentlibrary import MessageFactory as _

from nti.contentlibrary.interfaces import IContentValidator
from nti.contentlibrary.interfaces import IContentValidationError

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IContentValidationError)
class ContentValidationError(Exception):

    __external_class_name__ = "ContentValidationError"

    mime_type = mimeType = 'application/vnd.nextthought.content.validationerror'

    def __init__(self, message, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.message = message


class EmptyContentError(ContentValidationError):

    def __init__(self):
        ContentValidationError.__init__(self, _(u"Empty content"))


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
        except Exception as e:  # pylint: disable:broad-except
            exc_info = sys.exc_info()
            return e, exc_info
