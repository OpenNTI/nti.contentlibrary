#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Event listeners.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary.render import CONTENT_UNITS_QUEUE

from nti.contentlibrary.render.common import is_published

from nti.contentlibrary.render.processing import queue_add
from nti.contentlibrary.render.processing import queue_modified

from nti.contentlibrary.render.render import render_package

from nti.coremetadata.interfaces import IObjectPublishedEvent

from nti.externalization.interfaces import IObjectModifiedFromExternalEvent

@component.adapter(IRenderableContentPackage, IObjectPublishedEvent)
def _content_published(package, event):
    """
    When a renderable content package is published, push
    it into our processing factory
    """
    queue_add(CONTENT_UNITS_QUEUE, render_package, package)


@component.adapter(IRenderableContentPackage, IObjectModifiedFromExternalEvent)
def _content_updated(package, event):
    """
    When a persistent content library is modified, push
    it into our processing factory
    """
    if is_published(package):
        queue_modified(CONTENT_UNITS_QUEUE, render_package, package)
