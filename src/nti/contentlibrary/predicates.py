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

from nti.coremetadata.interfaces import IPublishablePredicate

from nti.contentlibrary.interfaces import IContentRendered
from nti.contentlibrary.interfaces import IRenderableContentUnit


@component.adapter(IRenderableContentUnit)
@interface.implementer(IPublishablePredicate)
class RenderableContentUnitPublishablePredicate(object):

    __slots__ = ()

    def __init__(self, *args):
        pass

    def is_published(self, unit, *args, **kwargs):
        return IContentRendered.providedBy(unit)
    isPublished = is_published
