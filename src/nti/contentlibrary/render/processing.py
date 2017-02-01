#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zc.blist import BList

from zope import component

from zope.component.hooks import getSite
from zope.component.hooks import site as current_site

from nti.async import create_job

from nti.contentlibrary.render.common import get_site
from nti.contentlibrary.render.common import object_finder

from nti.dataserver.interfaces import IDataserver

from nti.site.site import get_site_for_site_names

from nti.site.transient import TrivialSite

from nti.contentlibrary.render import get_factory

def _do_execute_job( *args, **kwargs ):
    args = BList( args )
    func = args.pop( 0 )
    object_id = kwargs.pop( 'source' )
    obj = object_finder( object_id )
    if obj is None:
        logger.info(
            'Object missing (deleted?) before event could be processed; event dropped. (%s) (%s)',
            object_id, func )
        return
    result = func( obj, *args, **kwargs )
    return result


def _get_job_site(job_site_name=None):
    old_site = getSite()
    if job_site_name is None:
        job_site = old_site
    else:
        dataserver = component.getUtility(IDataserver)
        ds_folder = dataserver.root_folder['dataserver2']
        with current_site(ds_folder):
            job_site = get_site_for_site_names((job_site_name,))

        if job_site is None or isinstance(job_site, TrivialSite):
            raise ValueError('No site found for (%s)' % job_site_name)
    return job_site


def _execute_job( *args, **kwargs ):
    """
    Performs the actual execution of a job.  We'll attempt to do
    so in the site the event occurred in, otherwise, we'll run in
    whatever site we are currently in.
    """
    event_site_name = kwargs.pop( 'site_name', None )
    event_site = _get_job_site(event_site_name)
    with current_site( event_site ):
        return _do_execute_job( *args, **kwargs )


def get_job_queue(name):
    factory = get_factory()
    return factory.get_queue(name)


def put_job(queue_name, jid, *args, **kwargs):
    queue = get_job_queue(queue_name)
    job = create_job(_execute_job, *args, **kwargs)
    job.id = jid
    queue.put(job)
    return job


def _get_obj_id(obj):
    return obj.ntiid


def add_to_queue(queue_name, func, obj, jid=None, **kwargs):
    site = get_site()
    doc_id = _get_obj_id( obj )
    jid = '%s_%s' % (doc_id, jid)
    return put_job(queue_name, func, jid=jid, source=doc_id, site_name=site, **kwargs)


def queue_add(name, func, obj, **kwargs):
    return add_to_queue(name, func, obj, jid='added', **kwargs)


def queue_modified(name, func, obj, **kwargs):
    return add_to_queue(name, func, obj, jid='modified', **kwargs)

