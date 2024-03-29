#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Event listeners.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.component.hooks import site

from zope.lifecycleevent.interfaces import IObjectCreatedEvent

from nti.base.interfaces import ICreated

from nti.contentlibrary.annotation import ContentUnitAnnotationUtility

from nti.contentlibrary.interfaces import ISiteLibraryFactory
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IContentUnitAnnotationUtility
from nti.contentlibrary.interfaces import IPersistentContentPackageLibrary

from nti.site.interfaces import IHostPolicyFolder

from nti.site.localutility import install_utility
from nti.site.localutility import install_utility_on_registration
from nti.site.localutility import uninstall_utility_on_unregistration

_LIBRARY_NAME = '++etc++library'

logger = __import__('logging').getLogger(__name__)


def install_site_content_library(local_site_manager, _=None):
    """
    When a new local site, representing a site (host) policy
    is added, install a site-local library and associated utilities
    into it. The library is sync'd after this is done.

    If you need to perform work, such as registering your own
    utility in the local site that uses the local library, listen for the component
    registration event, :class:`zope.interface.interfaces.IRegistered`,
    which is an ObjectEvent, whose object will be an
    :class:`nti.contentlibrary.interfaces.IPersistentContentPackageLibrary`.

    Although this function is ordinarily called as an event listener
    for a :class:`.INewLocalSite` event, it can also be called
    manually, passing in just a site manager. In that case, if there
    is no local library, and one can now be found, it will be created;
    if a local library already exists, nothing will be done.

    :returns: The site local content library, if one was found or installed.
    """

    if _ is None and _LIBRARY_NAME in local_site_manager:
        lib = local_site_manager[_LIBRARY_NAME]
        logger.debug("Nothing to do for site %s, library already present %s",
                     local_site_manager, lib)
        return lib

    gsm = component.getGlobalSiteManager()
    global_library = gsm.queryUtility(IContentPackageLibrary)
    if global_library is None:
        logger.warning(
            "New site installed without global library; will not have local library")
        return

    local_site = local_site_manager.__parent__
    assert bool(local_site.__name__), "sites must be named"

    site_library_factory = ISiteLibraryFactory(global_library, None)
    if site_library_factory is None:
        logger.warning("No site factory for %s; should only happen in tests",
                       global_library)
        return

    # pylint: disable=too-many-function-args
    library = site_library_factory.library_for_site_named(local_site.__name__)
    logger.info("Installing site library %s for %s",
                library, local_site.__name__)
    assert IPersistentContentPackageLibrary.providedBy(library)

    with site(local_site):
        # Install and sync in this site so the right utilities and event
        # listeners are found.
        # Before we install the library (which fires a registration event that things might
        # be listening for) set up the dependent utilities
        install_utility(ContentUnitAnnotationUtility(),
                        '++etc++contentannotation',
                        IContentUnitAnnotationUtility,
                        local_site_manager)
        install_utility(library,
                        _LIBRARY_NAME,
                        IPersistentContentPackageLibrary,
                        local_site_manager)
        library.syncContentPackages()
        return library


# Bundle-related subscribers


from zope.interface.interfaces import IRegistered
from zope.interface.interfaces import IUnregistered

from nti.contentlibrary.bundle import ContentPackageBundleLibrary

from nti.contentlibrary.interfaces import IContentPackageBundleLibrary
from nti.contentlibrary.interfaces import IContentPackageLibraryDidSyncEvent
from nti.contentlibrary.interfaces import ISyncableContentPackageBundleLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

# because it might be in traversal paths
_BUNDLE_LIBRARY_NAME = 'ContentPackageBundles'


@component.adapter(IPersistentContentPackageLibrary, IRegistered)
def install_bundle_library(_, event):
    """
    When a new persistent library is installed, beside it we
    put something to manage (persistent) content bundles, driven
    off the bucket that the library manages.
    """
    install_utility_on_registration(ContentPackageBundleLibrary(),
                                    _BUNDLE_LIBRARY_NAME,
                                    IContentPackageBundleLibrary,
                                    event)


@component.adapter(IPersistentContentPackageLibrary, IUnregistered)
def uninstall_bundle_library(_, event):
    uninstall_utility_on_unregistration(_BUNDLE_LIBRARY_NAME,
                                        IContentPackageBundleLibrary,
                                        event)


@component.adapter(IPersistentContentPackageLibrary,
                   IContentPackageLibraryDidSyncEvent)
def sync_bundles_when_library_synched(library, _):
    """
    When a persistent content library is synchronized
    with the disk contents, whether or not anything actually changed,
    we also synchronize the corresponding bundle library.
    (Because they could change independently and in unknown ways)
    """

    # Find the local site manager
    site_manager = component.getSiteManager(library)
    if library.__parent__ is not site_manager:
        msg = "Expected to find persistent library in its own site; refusing to sync"
        logger.warning(msg)
        return

    bundle_library = site_manager.getUtility(IContentPackageBundleLibrary)
    assert bundle_library.__parent__ is site_manager, \
           "Make sure we got the immediate parent"

    enumeration = IDelimitedHierarchyContentPackageEnumeration(library)
    enumeration_root = enumeration.root

    # pylint: disable=no-member
    bundle_bucket = enumeration_root.getChildNamed(bundle_library.__name__)
    if bundle_bucket is None:
        logger.info("Not synchronizing: no directory named %s in %s for library %s",
                    bundle_library.__name__,
                    getattr(
                        enumeration_root,
                        'absolute_path',
                        enumeration_root),
                    library)
        return

    logger.info("Synchronizing bundle library %s in site %s from directory %s",
                bundle_library, site_manager.__parent__.__name__,
                getattr(bundle_bucket, 'absolute_path', bundle_bucket))
    syncable = ISyncableContentPackageBundleLibrary(bundle_library)
    # pylint: disable=too-many-function-args
    syncable.syncFromBucket(bundle_bucket)


@component.adapter(IHostPolicyFolder, IObjectCreatedEvent)
def on_site_created(folder, unused_event=None):
    if ICreated.providedBy(folder):
        site_manager = folder.getSiteManager()
        install_site_content_library(site_manager)
        install_utility(ContentPackageBundleLibrary(),
                        _BUNDLE_LIBRARY_NAME,
                        IContentPackageBundleLibrary,
                        site_manager)
