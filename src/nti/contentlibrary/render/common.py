#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

import isodate

from zope.component.hooks import getSite

from nti.coremetadata.interfaces import IPublishable

from nti.ntiids.ntiids import find_object_with_ntiid

def is_published(obj):
    return not IPublishable.providedBy(obj) or obj.is_published()
isPublished = is_published


def get_site(site_name=None):
    if site_name is None:
        site = getSite()
        site_name = site.__name__ if site is not None else None
    return site_name


def datetime_isoformat(now=None):
    now = now or datetime.now()
    return isodate.datetime_isoformat(now)


def object_finder(doc_id):
    return find_object_with_ntiid(doc_id)
