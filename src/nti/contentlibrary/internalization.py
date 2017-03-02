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

from zope.dublincore.interfaces import IDCExtended
from zope.dublincore.interfaces import IDCDescriptiveProperties

from nti.contentlibrary.interfaces import IEditableContentUnit
from nti.contentlibrary.interfaces import IDelimitedHierarchyKey
from nti.contentlibrary.interfaces import IRenderableContentUnit
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.coremetadata.interfaces import IPublishable

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectUpdater
from nti.externalization.interfaces import StandardExternalFields

NTIID = StandardExternalFields.NTIID
MIME_TYPE = StandardExternalFields.MIMETYPE


@component.adapter(IEditableContentUnit)
@interface.implementer(IInternalObjectUpdater)
class _EditableContentUnitUpdater(InterfaceObjectIO):

    ALLOWED_KEYS =  tuple(IPublishable.names()) + \
                    tuple(IDCExtended.names())  + \
                    tuple(IDCDescriptiveProperties.names()) + \
                    ('icon', 'contentType', 'contents', 'ntiid', NTIID, MIME_TYPE)

    _ext_iface_upper_bound = IEditableContentUnit

    def _clean_input(self, parsed):
        for name in list(parsed.keys()):
            if name not in self.ALLOWED_KEYS:
                parsed.pop(name, None)
        if not 'ntiid' in parsed and NTIID in parsed:
            parsed['ntiid'] = parsed.get(NTIID)
        return parsed

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        parsed = self._clean_input(parsed)
        if IDelimitedHierarchyKey.providedBy(parsed.get('icon')):
            raise ValueError("Cannot set icon to a hierarchy item")
        result = super(_EditableContentUnitUpdater, self).updateFromExternalObject(parsed,*args, **kwargs)
        if 'contents' in parsed:
            decoded = str(parsed['contents'])
            self._ext_self.contents = decoded
        if 'contentType' in parsed:
            self._ext_self.contentType = str(parsed['contentType'])
        return result


@component.adapter(IEditableContentPackage)
@interface.implementer(IInternalObjectUpdater)
class _EditableContentPackageUpdater(_EditableContentUnitUpdater):

    ALLOWED_KEYS = _EditableContentUnitUpdater.ALLOWED_KEYS + \
                    ('index_last_modified', 'indexLastModified')

    def _clean_input(self, parsed):
        parsed = super(_EditableContentPackageUpdater, self)._clean_input(parsed)
        if not 'index_last_modified' in parsed and 'indexLastModified' in parsed:
            parsed['index_last_modified'] = parsed.get('indexLastModified')
        return parsed

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        result = super(_EditableContentPackageUpdater, self).updateFromExternalObject(parsed, *args, **kwargs)
        if 'index_last_modified' in parsed:
            self._ext_self.index_last_modified = parsed['index_last_modified']
        return result

@component.adapter(IRenderableContentUnit)
@interface.implementer(IInternalObjectUpdater)
class _RenderableContentUnitUpdater(_EditableContentUnitUpdater):
    _ext_iface_upper_bound = IRenderableContentUnit


@component.adapter(IRenderableContentPackage)
@interface.implementer(IInternalObjectUpdater)
class _RenderableContentPackageUpdater(_EditableContentPackageUpdater):
    _ext_iface_upper_bound = IRenderableContentPackage
