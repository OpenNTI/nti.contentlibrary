#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.contentlibrary.interfaces import IEditableContentUnit
from nti.contentlibrary.interfaces import IRenderableContentUnit

from nti.dublincore.interfaces import IDCOptionalDescriptiveProperties

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectUpdater
from nti.externalization.interfaces import StandardExternalFields

MIME_TYPE = StandardExternalFields.MIMETYPE


@component.adapter(IEditableContentUnit)
@interface.implementer(IInternalObjectUpdater)
class _EditableContentUnitUpdater(InterfaceObjectIO):

    ALLOWED_KEYS = tuple(IDCOptionalDescriptiveProperties.names()) + \
        ('icon', 'thumbnail', 'content', MIME_TYPE)

    def _clean_input(self, parsed):
        for name in list(parsed.keys()):
            if name not in self.ALLOWED_KEYS:
                parsed.pop(name, None)
        return parsed

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        parsed = self._clean_input(parsed)
        result = super(_EditableContentUnitUpdater,
                       self).updateFromExternalObject(parsed, *args, **kwargs)
        return result


@component.adapter(IRenderableContentUnit)
@interface.implementer(IInternalObjectUpdater)
class _RenderableContentUnitUpdater(_EditableContentUnitUpdater):
    pass
