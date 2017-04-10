#!/Sr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes useful for working with libraries.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import numbers
import warnings

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.component.hooks import getSite

from zope.event import notify

from zope.intid.interfaces import IIntIds

from ZODB.interfaces import IBroken
from ZODB.interfaces import IConnection

from ZODB.POSException import POSError
from ZODB.POSException import ConnectionStateError

from persistent import Persistent

from BTrees.OOBTree import OOBTree

from nti.contentlibrary import AUTHORED_PREFIX

from nti.contentlibrary.interfaces import INoAutoSync
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IGlobalContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IPersistentContentUnit
from nti.contentlibrary.interfaces import ContentPackageAddedEvent
from nti.contentlibrary.interfaces import ContentPackageRemovedEvent
from nti.contentlibrary.interfaces import IContentPackageEnumeration
from nti.contentlibrary.interfaces import ContentPackageReplacedEvent
from nti.contentlibrary.interfaces import ContentPackageUnmodifiedEvent
from nti.contentlibrary.interfaces import IEditableContentPackageLibrary
from nti.contentlibrary.interfaces import ContentPackageLibraryDidSyncEvent
from nti.contentlibrary.interfaces import ContentPackageLibraryWillSyncEvent
from nti.contentlibrary.interfaces import ContentPackageLibraryModifiedOnSyncEvent
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.contentlibrary.synchronize import SynchronizationResults
from nti.contentlibrary.synchronize import ContentRemovalException
from nti.contentlibrary.synchronize import UnmatchedRootNTIIDException
from nti.contentlibrary.synchronize import LibrarySynchronizationResults

from nti.contentlibrary.utils import get_content_packages

from nti.externalization.persistence import NoPickle

from nti.intid.common import addIntId
from nti.intid.common import removeIntId

from nti.property.property import alias

from nti.site.localutility import queryNextUtility


@interface.implementer(IContentPackageEnumeration)
class AbstractContentPackageEnumeration(object):
    """
    Base class providing some semantic helpers for enumeration.

    In any case, to make this class concrete, see
    :meth:`_package_factory` and :meth:`_possible_content_packages`.

    """

    __name__ = None
    __parent__ = None

    def _package_factory(self, possible_content_package):
        """
        A callable object that is passed each item from :attr:`possible_content_packages`
        and returns either a package factory, or `None`.

        This should not fire the ``created`` event.
        """
        return None

    def _possible_content_packages(self):
        """
        A sequence of objects to introspect for :class:`.IContentPackage` objects;
        typically strings. These are passed to :attr:`package_factory`
        """
        return ()

    def enumerateContentPackages(self):
        """
        Returns a sequence of IContentPackage items, as created by
        invoking the ``self._package_factory`` on each item returned
        from iterating across ``self._possible_content_packages``.
        """
        titles = []
        for path in self._possible_content_packages():
            title = self._package_factory(path)
            if title:
                titles.append(title)
        return titles


@interface.implementer(IDelimitedHierarchyContentPackageEnumeration)
class AbstractDelimitedHiercharchyContentPackageEnumeration(AbstractContentPackageEnumeration):
    """
    An object that works with a root bucket to enumerate content paths.
    We override :meth:`_possible_content_packages`, you still
    need to override :meth:`_package_factory` at a minimum.
    """

    root = None

    def _include(self, bucket):
        # Exclude any authored content on disk from consideration
        return not bucket.name.startswith(AUTHORED_PREFIX)

    def _possible_content_packages(self):
        """
        Returns the children of the root.
        """

        root = self.root
        if root is None:
            return ()
        result = root.enumerateChildren()
        return (x for x in result if self._include(x))


def add_to_connection(context, obj):
    connection = IConnection(context, None)
    if connection is not None and IConnection(obj, None) is None:
        connection.add(obj)
        return True
    return False


def is_indexable(obj):
    try:
        return  not IBroken.providedBy(obj) \
            and IPersistentContentUnit.providedBy(obj)
    except (TypeError, POSError):  # Broken object
        return False


def register_content_units(context, content_unit):
    """
    Recursively register content units.
    """
    intids = component.queryUtility(IIntIds)
    if intids is None:
        return

    def _register(obj):
        add_to_connection(context, obj)
        for child in obj.children or ():
            _register(child)
        if is_indexable(obj):
            intid = intids.queryId(obj)
            if intid is None:
                addIntId(obj)
    _register(content_unit)


def unregister_content_units(context):
    """
    Recursively unregister content units.
    """
    intids = component.queryUtility(IIntIds)
    if intids is None:
        return

    def _unregister(obj):
        for child in obj.children or ():
            _unregister(child)
        if is_indexable(obj):
            intid = intids.queryId(obj)
            if intid is not None:
                removeIntId(obj)

    _unregister(context)


@interface.implementer(IEditableContentPackageLibrary)
class AbstractContentPackageLibrary(object):
    """
    A library that uses an enumeration and cooperates with parent
    libraries in the component hierarchy to build a complete
    library.

    We become the parent of the enumeration, so it is critical that
    enumerations are not shared between libraries; an enumeration
    defines a library, so those libraries would be semantically
    equivalent.
    """

    # Placeholder for prefixes that should be applied when generating
    # URLs for items in this library.
    url_prefix = ''

    # A place where we will cache the list of known
    # content packages. A value of `None` means we have never
    # been synced. The behaviour of iterating content packages
    # to implicitly sync is deprecated.
    _contentPackages = None

    # storage of content units by their ntiids
    _contentUnitsByNTIID = None

    # The enumeration we will use when asked to sync
    # content packages.
    _enumeration = None

    # When we sync, we capture the `lastModified` timestamp
    # of the enumeration, if it provides it.
    _enumeration_last_modified = 0

    # library last modified timestamp
    _last_modified = 0

    __name__ = 'Library'
    __parent__ = None

    def __init__(self, enumeration, prefix='', **kwargs):
        self._enumeration = enumeration
        enumeration.__parent__ = self
        assert enumeration is not None
        if prefix:
            self.url_prefix = prefix

    def _is_syncable(self, package):
        """
        Determine if the give package is syncable.
        """
        return not INoAutoSync.providedBy(package)

    @property
    def _root_name(self):
        root = getattr(self._enumeration, 'root', None)
        name = root.__name__ if root is not None else self.__name__
        return name

    def _get_content_units_for_package(self, package):
        result = []

        def _recur(unit):
            result.append(unit)
            for child in unit.children:
                _recur(child)
        _recur(package)
        return result

    def _record_units_by_ntiid(self, package):
        for unit in self._get_content_units_for_package(package):
            self._contentUnitsByNTIID[unit.ntiid] = unit

    def _unrecord_units_by_ntiid(self, package):
        for unit in self._get_content_units_for_package(package):
            self._contentUnitsByNTIID.pop(unit.ntiid, None)

    def _do_addContentPackages(self, added, event=True,
                               lib_sync_results=None, params=None, results=None):
        for new in added:
            # add to maps
            self._record_units_by_ntiid(new)
            self._contentPackages[new.ntiid] = new
            # take ownership
            new.__parent__ = self
            # get intids
            register_content_units(self, new)
            # notify
            if event:
                lifecycleevent.created(new)
                notify(ContentPackageAddedEvent(new, params, results))
            # add to sync results
            if lib_sync_results is not None:
                lib_sync_results.added(new.ntiid)

    def _do_removeContentPackages(self, removed, event=True, unregister=True,
                                  lib_sync_results=None, params=None, results=None):
        for old in removed or ():
            # remove from maps
            self._unrecord_units_by_ntiid(old)
            self._contentPackages.pop(old.ntiid, None)
            # notify removal (intids are kept)
            if event:
                notify(ContentPackageRemovedEvent(old, params, results))
            # ground
            old.__parent__ = None
            # remove from intid facility
            if unregister:
                unregister_content_units(old)
            # record in sync results
            if lib_sync_results is not None:
                lib_sync_results.removed(old.ntiid)

    def add(self, package, event=True):
        self._last_modified = time.time()
        self._do_addContentPackages((package,), event=event)
    append = add

    def remove(self, package, event=True, unregister=True):
        self._last_modified = time.time()
        self._do_removeContentPackages((package,),
                                       event=event,
                                       unregister=unregister)

    def _do_updateContentPackages(self, changed, lib_sync_results=None,
                                  params=None, results=None):
        result = []
        for new, old in changed:
            # check ntiid changes
            if new.ntiid != old.ntiid:
                raise UnmatchedRootNTIIDException(
                    "Package NTIID changed from %s to %s" % (old.ntiid, new.ntiid))
            self._contentPackages[new.ntiid] = new
            self._unrecord_units_by_ntiid(old)
            self._record_units_by_ntiid(new)
            new.__parent__ = self  # ownership
            # XXX CS/JZ, 2-04-15 DO NEITHER call lifecycleevent.created nor
            # lifecycleevent.added on 'new' objects as modified events subscribers
            # are expected to handle any change
            register_content_units(self, new)
            if lib_sync_results is not None:
                lib_sync_results.modified(new.ntiid)  # register
            # Note that this is the special event that shows both objects.
            notify(ContentPackageReplacedEvent(new, old, params, results))
            # CS/JZ, 2-04-15  DO NOT call lifecycleevent.removed on this
            # objects b/c this may unregister things we don't want to leaving
            # the database in a invalid state
            unregister_content_units(old)
            old.__parent__ = None  # ground
            # track
            result.append(new)
        return result

    def replace(self, package, results=None):
        old = self._contentPackages[package.ntiid]
        return self._do_updateContentPackages(((package, old),), results=results)

    def _get_content_units_by_ntiid(self, packages):
        """
        Get our ntiid to content unit map.
        """
        result = OOBTree()
        for package in packages:
            for unit in self._get_content_units_for_package(package):
                result[unit.ntiid] = unit
        return result

    def _do_completeSyncPackages(self, unmodified, lib_sync_results, params, results,
                                 do_notify=True):
        if do_notify:
            # Signal what packages WERE NOT modified
            for package in unmodified or ():
                notify(ContentPackageUnmodifiedEvent(package, params, results))

            # Finish up by saying that we sync'd, even if nothing changed
            notify(ContentPackageLibraryDidSyncEvent(self, params, results))

        # set last sync time
        self._enumeration.lastSynchronized = time.time()
        return lib_sync_results

    def _get_current_packages(self):
        site = getSite()
        site = site.__name__ if site is not None else 'dataserver2'
        if      site == 'dataserver2' \
            or component.queryUtility(IIntIds) is None \
            or component.getGlobalSiteManager() == component.getSiteManager():
            return self._contentPackages.values()
        else:
            return get_content_packages(sites=(site,))

    def syncContentPackages(self, params=None, results=None):
        """
        Fires created, added, modified, or removed events for each
        content package, as appropriate.
        """
        packages = params.ntiids if params is not None else ()
        results = SynchronizationResults() if results is None else results
        notify(ContentPackageLibraryWillSyncEvent(self, params))

        lib_sync_results = LibrarySynchronizationResults(Name=self._root_name)
        results.add(lib_sync_results)

        never_synced = False
        if self._contentPackages is None:
            never_synced = True
            self._contentPackages = OOBTree()
            self._contentUnitsByNTIID = OOBTree()
        old_content_packages = self._get_current_packages()
        old_content_packages = {x.ntiid:x for x in old_content_packages}

        # Make sure we get ALL packages
        new_content_packages = self._enumeration.enumerateContentPackages()
        new_content_packages = {x.ntiid:x for x in new_content_packages}

        enumeration = self._enumeration
        enumeration_last_modified = getattr(enumeration, 'lastModified', 0)

        # Before we fire any events, compute all the work so that we can present
        # a consistent view to any listeners that will be watching.
        removed = []
        changed = []
        unmodified = []
        if not packages:  # no filter
            added = [package
                     for ntiid, package in new_content_packages.items()
                     if ntiid not in old_content_packages]
        else:
            # Choosing this path WILL NOT add any new packages
            added = ()

        for old_key, old_package in old_content_packages.items():
            if not self._is_syncable(old_package):
                unmodified.append(old_package)
                continue
            new_package = new_content_packages.get(old_key)
            if new_package is None:
                removed.append(old_package)
            elif old_package.lastModified < new_package.lastModified:
                changed.append((new_package, old_package))
            else:
                unmodified.append(old_package)

        if removed or added or changed or never_synced:
            # CS/JZ, 1-29-15 We need this before event firings because some code
            # (at least question_map.py used to) relies on getting the new content units
            # via pathToNtiid.
            # TODO: Verify nothing else is doing so.
            self._enumeration_last_modified = enumeration_last_modified

            if not never_synced:
                logger.info("Library %s adding packages %s", self, added)
                logger.info("Library %s removing packages %s", self, removed)
                logger.info("Library %s changing packages %s", self, changed)

            if removed and params is not None and not params.allowRemoval:
                raise ContentRemovalException(
                    "Cannot remove content packages without explicitly allowing it")

            # Now fire the events letting listeners (e.g., index and question adders)
            # know that we have content. Randomize the order of this across worker
            # processes so that we don't collide too badly on downloading indexes if need be
            # (only matters if we are not preloading).
            # Do this in greenlets/parallel. This can radically speed up
            # S3 loading when we need the network.
            # XXX: Does order matter?
            # XXX: Note that we are not doing it in parallel, because if we need
            # ZODB site access, we can have issues. Also not we're not
            # randomizing because we expect to be preloaded.
            self._do_removeContentPackages(removed,
                                           event=True,
                                           params=params,
                                           results=results,
                                           lib_sync_results=lib_sync_results)

            modified = self._do_updateContentPackages(changed,
                                                      params=params,
                                                      results=results,
                                                      lib_sync_results=lib_sync_results)

            self._do_addContentPackages(added,
                                        event=True,
                                        params=params,
                                        results=results,
                                        lib_sync_results=lib_sync_results)

            # Ok, new let people know that 'contentPackages' changed
            attributes = lifecycleevent.Attributes(IContentPackageLibrary,
                                                   'contentPackages')
            event = ContentPackageLibraryModifiedOnSyncEvent(self,
                                                             added=added,
                                                             removed=removed,
                                                             changed=modified,
                                                             descriptions=attributes,
                                                             params=params,
                                                             results=results,)
            notify(event)

        self._do_completeSyncPackages(unmodified,
                                      lib_sync_results,
                                      params,
                                      results)
        return lib_sync_results

    def _checkSync(self):
        if self._contentPackages is None:
            warnings.warn("Please sync the library first.", stacklevel=2)
            warnings.warn("Please sync the library first.", stacklevel=3)
            self.syncContentPackages()

    def _get_contentPackages(self):
        self._checkSync()
        # We would like to use a generator here, to avoid
        # copying in case of a parent, but our interface
        # requires that this be indexable, for some reason.
        # Note that our values always take precedence over anything
        # we get from the parent
        parent = queryNextUtility(self, IContentPackageLibrary)
        if parent is None:
            # We can directly return our store
            return self._contentPackages
        # Now duplicate and merge with parent
        contentPackages = dict(self._contentPackages or {})
        for parent_package in parent.contentPackages:
            if parent_package.ntiid not in self._contentPackages:
                contentPackages[parent_package.ntiid] = parent_package
        return contentPackages

    @property
    def contentPackages(self):
        return list(self._get_contentPackages().values())

    @property
    def contentUnitsByNTIID(self):
        self._checkSync()
        parent = queryNextUtility(self, IContentPackageLibrary)
        if parent is None:
            return self._contentUnitsByNTIID
        # Now duplicate and merge with parent
        contentUnitsByNTIID = dict(self._contentUnitsByNTIID or {})
        for ntiid, unit in parent.contentUnitsByNTIID.items():
            if ntiid not in self._contentUnitsByNTIID:
                contentUnitsByNTIID[ntiid] = unit
        return contentUnitsByNTIID

    def removeInvalidContentUnits(self):
        result = dict()
        self._checkSync()
        intids = component.getUtility(IIntIds)
        for ntiid, unit in list(self._contentUnitsByNTIID.items()):
            if intids.queryId(unit) is None:
                result[ntiid] = unit
                del self._contentUnitsByNTIID[ntiid]

        parent = queryNextUtility(self, IContentPackageLibrary)
        if parent is not None:
            try:
                result.update(parent.removeInvalidContentUnits())
            except AttributeError:
                pass
        return result
    removeInvalid = removeInvalidContentUnits

    def __delattr__(self, name):
        """
        As a nuclear option, you can delete the property `contentPackages`
        to enforce a complete removal of the entire value, and the next
        sync will be from scratch.
        """
        if name == 'contentPackages':
            self.resetContentPackages()
        else:
            super(AbstractContentPackageLibrary, self).__delattr__(name)

    titles = alias('contentPackages')

    def resetContentPackages(self):
        """
        As a nuclear option, this enforces a complete removal of all
        the packages directly stored here. The next sync will be from
        scratch.
        """

        try:
            # let subclasses be persistent
            self._p_activate()
        except AttributeError:
            pass

        if '_contentPackages' not in self.__dict__:
            return

        # When we are uncached to force re-enumeration,
        # we need to send the corresponding object removed events
        # so that people that care can clean up.
        # TODO: What's the right order for this, before or after
        # we do the delete?
        if self._contentPackages:
            for title in self._contentPackages.values():
                lifecycleevent.removed(title)
                unregister_content_units(title)
                title.__parent__ = None  # ground

        del self._contentUnitsByNTIID
        del self._contentPackages

    @property
    def enumeration(self):
        return self._enumeration

    @property
    def createdTime(self):
        try:
            return self._enumeration.createdTime
        except AttributeError:
            return 0

    @property
    def lastModified(self):
        """
        This object is deemed to be last modified at least as recently as any
        of its content packages and its enumeration.
        """
        # Refuse to do this if we're not sync'd!
        if self._contentPackages is None:
            return -1

        # We used to base this on the packages `index_last_modified`, now
        # we take the max of our enumeration and last add/remove.
        lastModified = max(self._enumeration_last_modified,
                           self._last_modified)
        return lastModified

    def __getitem__(self, key):
        """
        :return: The LibraryEntry having an ntiid that matches `key`.
        """
        if isinstance(key, numbers.Integral):
            if key != 0:
                raise TypeError(
                    "Integers other than 0---first---not supported")
            # This should only be done by tests
            return list(self.contentPackages)[key]

        # In the past this worked even if the library had not been synced
        # because it used self.contentPackages to do the implicit sync.
        try:
            result = self._contentPackages[key]
        except KeyError:
            # We no longer check titles
            parent = queryNextUtility(self, IContentPackageLibrary)
            if parent is None:
                raise KeyError(key)
            result = parent.__getitem__(key)
        return result

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    # Other container methods
    def __delitem__(self, key):
        raise TypeError("deletion not supported")

    def __setitem__(self, key):
        raise TypeError("setting not supported")

    def __len__(self):
        # XXX: This doesn't make much sense
        return len(self._contentPackages)

    def __contains__(self, key):
        return self.get(key) is not None

    def __bool__(self):
        # We are always true, regardless of content
        return True
    __nonzero__ = __bool__

    @property
    def lastSynchronized(self):
        try:
            return self._enumeration.lastSynchronized
        except AttributeError:
            return 0

    def _get_content_unit(self, key):
        """
        Fetch the content unit referenced by the given ntiid.
        """
        if not key:
            return None
        result = self._contentUnitsByNTIID.get(key)
        if result is None:
            # Check our parent
            parent = queryNextUtility(self, IContentPackageLibrary)
            if parent is not None:
                result = parent._get_content_unit(key)
        return result

    def pathToNTIID(self, ntiid):
        """
        Returns a list of TOCEntry objects in order until
        the given ntiid is encountered, or None if the id cannot be found.
        """
        result = None
        unit = self._get_content_unit(ntiid)
        if unit is not None:
            result = [unit]
            # Now iterate upwards and fetch our parents all the way
            # to the content package.

            def _get_parent_unit(item):
                if IContentPackage.providedBy(item):
                    return
                try:
                    parent = item.__parent__
                    if parent is not None:
                        result.append(parent)
                        _get_parent_unit(parent)
                except AttributeError:
                    pass
            _get_parent_unit(unit)
            result.reverse()
        return result

    def childrenOfNTIID(self, ntiid):
        """
        Returns a flattened list of all the children entries of ntiid in
        no particular order. If there are no children, returns an empty list.

        :return: Always returns a fresh list.
        """
        result = []
        parent = self._get_content_unit(ntiid)
        if parent is not None:
            def rec(toc, accum):
                accum.extend(toc.embeddedContainerNTIIDs)
                for child in toc.children:
                    rec(child, accum)
                accum.append(toc.ntiid)
            rec(parent, result)
            # And the last thing we did was append the parent
            # itself, so take it off; we only want the children
            result.pop()
        return result

    def pathsToEmbeddedNTIID(self, ntiid):
        """
        Returns a list of paths (sequences of TOCEntry objects); the last
        element in each path is a :class:`.IContentUnit` that contains an
        embedded reference to the given NTIID. That is, the returned list
        describes all the locations that the NTIID is known to be referenced
        for use as a subcontainer. The returned list of paths is in no
        particular order.
        """
        result = []
        for unit in self._contentUnitsByNTIID.values():
            if ntiid in unit.embeddedContainerNTIIDs:
                result.append(self.pathToNTIID(unit.ntiid))
        if not result:
            # Check our parent
            parent = queryNextUtility(self, IContentPackageLibrary)
            if parent is not None:
                result = parent.pathsToEmbeddedNTIID(ntiid)
        return result


@NoPickle
@interface.implementer(IAttributeAnnotatable)
class GlobalContentPackageLibrary(AbstractContentPackageLibrary):
    """
    A content package library meant only to be installed in the global
    (non-persistent) registry. This type of library must be synchronized
    on every startup.
    """

    def _get_contentPackages(self):
        result = super(GlobalContentPackageLibrary, self)._get_contentPackages()
        for package in result.values():
            if not IGlobalContentPackage.providedBy(package):
                interface.alsoProvides(package, IGlobalContentPackage)
        return result

    def removeInvalidContentUnits(self):
        return dict()
    removeInvalid = removeInvalidContentUnits


class _EmptyEnumeration(AbstractContentPackageEnumeration):

    def enumerateContentPackages(self):
        return ()


def EmptyLibrary(prefix=''):
    """
    A library that is perpetually empty.
    """
    return GlobalContentPackageLibrary(_EmptyEnumeration(), prefix=prefix)


class PersistentContentPackageLibrary(Persistent,
                                      AbstractContentPackageLibrary):
    """
    A library that is meant to be persisted. It
    generally does not need to be synchronized on
    every startup, only when content on disk has changed.
    """

    def __repr__(self):
        try:
            return super(PersistentContentPackageLibrary, self).__repr__()
        except ConnectionStateError:
            return object.__repr__(self)
