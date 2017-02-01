#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for rendering content units.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import component

from nti.contentlibrary.render.interfaces import IContentQueueFactory

CONTENT_UNITS_QUEUE = '++etc++contentlibrary++queue++contentunits'

QUEUE_NAMES = (CONTENT_UNITS_QUEUE,)

def get_factory():
    return component.getUtility(IContentQueueFactory)
