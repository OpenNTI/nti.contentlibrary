#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectUpdater


@interface.implementer(IInternalObjectUpdater)
class _EditableContentPacakgeUpdater(InterfaceObjectIO):

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        result = super(_EditableContentPacakgeUpdater, 
                       self).updateFromExternalObject(parsed, *args, **kwargs)
        return result
