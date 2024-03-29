#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of content bundles.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from BTrees.OOBTree import OOSet
from BTrees.OOBTree import difference as ooset_difference

from ZODB.POSException import ConnectionStateError

from zope import component
from zope import interface
from zope import lifecycleevent

# Because we only expect to store persistent versions
# of these things, and we expect to update them directly
# in place, we make them attribute annotatable.
from zope.annotation.interfaces import IAttributeAnnotatable

from zope.container.contained import Contained

from zope.event import notify

from zope.location.location import locate

from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.base.interfaces import ICreated

from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.contentlibrary import VENDOR_INFO_NAME
from nti.contentlibrary import MissingContentBundleNTIIDException

from nti.contentlibrary.interfaces import IDisplayableContent
from nti.contentlibrary.interfaces import IContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary
from nti.contentlibrary.interfaces import IEditableContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageBundleVendorInfo
from nti.contentlibrary.interfaces import IPublishableContentPackageBundle
from nti.contentlibrary.interfaces import ContentPackageBundleVendorInfoSynchronized

from nti.contentlibrary.presentationresource import DisplayableContentMixin

from nti.coremetadata.interfaces import SYSTEM_USER_ID

from nti.dublincore.time_mixins import CreatedAndModifiedTimeMixin

from nti.externalization.persistence import NoPickle

from nti.externalization.representation import WithRepr

from nti.property.property import alias

from nti.publishing.mixins import PublishableMixin

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createFieldProperties
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.wref.interfaces import IWeakRef

from nti.zodb.persistentproperty import PersistentPropertyHolder

DEFAULT_BUNDLE_MIME_TYPE = 'application/vnd.nextthought.contentpackagebundle'
PUBLISHABLE_BUNDLE_MIME_TYPE = 'application/vnd.nextthought.publishablecontentpackagebundle'

logger = __import__('logging').getLogger(__name__)


@WithRepr
@interface.implementer(IContentPackageBundle, IAttributeAnnotatable, ICreated)
class ContentPackageBundle(CreatedAndModifiedTimeMixin,
                           DisplayableContentMixin,
                           Contained,
                           SchemaConfigured):

    """
    Basic implementation of a content package bundle.
    """
    __external_can_create__ = False
    __external_class_name__ = 'ContentPackageBundle'

    # Equality and hashcode not defined on purpose,
    # identity semantics for now!

    # Be careful not to overwrite what we inherit
    createFieldProperties(IDisplayableContent,
                          omit='PlatformPresentationResources')
    createDirectFieldProperties(IContentPackageBundle)

    RestrictedAccess = FP(IContentPackageBundle['RestrictedAccess'])

    # the above defined the ntiid property and the name
    # property, but the ntiid property has the constraint on it
    # that we need.
    __name__ = alias('ntiid')

    # IDCExtendedProperties.
    # Note that we're overriding these to provide
    # default values, thus losing the FieldProperty
    # implementation
    creators = ()
    subjects = ()
    contributors = ()
    publisher = u''

    creator = SYSTEM_USER_ID

    @property
    def PlatformPresentationResources(self):
        """
        If we do not have a set of presentation assets,
        we echo the first content package we have that does contain
        them. This should simplify things for the clients.
        """
        ours = super(ContentPackageBundle, self).PlatformPresentationResources
        if ours:  # pylint: disable=using-constant-test
            return ours

        # pylint: disable=no-member
        for package in self.ContentPackages or ():
            theirs = package.PlatformPresentationResources
            if theirs:
                return theirs
        return ()


@interface.implementer(IEditableContentPackageBundle)
class PersistentContentPackageBundle(ContentPackageBundle,
                                     PersistentPropertyHolder):
    """
    A persistent implementation of content package bundles.

    As required, references to content packages are
    maintained weakly.
    """
    __external_can_create__ = True
    __external_class_name__ = 'ContentPackageBundle'

    mime_type = mimeType = DEFAULT_BUNDLE_MIME_TYPE

    # NOTE we don't extend the convenience class PersistentCreatedAndModifiedTimeObject
    # from time_mixins, because it re-introduces the CreatedAndModifiedTimeMixin
    # we got from ContentPackageBundle; that makes it hard to further subclass.

    _ContentPackages_wrefs = ()

    def _set_ContentPackages(self, packages):
        self._ContentPackages_wrefs = OOSet(IWeakRef(p) for p in packages)

    def _get_ContentPackages(self):
        result = list()
        for x in self._ContentPackages_wrefs:
            x = x()
            if x is not None:
                result.append(x)
        return result
    ContentPackages = property(_get_ContentPackages, _set_ContentPackages)

    def add(self, context):
        if not isinstance(self._ContentPackages_wrefs, OOSet):
            self._ContentPackages_wrefs = OOSet(self._ContentPackages_wrefs)
        self._ContentPackages_wrefs.add(IWeakRef(context))

    def remove(self, context):
        if not isinstance(self._ContentPackages_wrefs, OOSet):
            self._ContentPackages_wrefs = OOSet(self._ContentPackages_wrefs)
        try:
            self._ContentPackages_wrefs.remove(IWeakRef(context))
            return True
        except KeyError:
            return False

    def __repr__(self):
        try:
            return super(PersistentContentPackageBundle, self).__repr__()
        except ConnectionStateError:
            return object.__repr__(self)

    def __str__(self):
        try:
            return super(PersistentContentPackageBundle, self).__str__()
        except ConnectionStateError:
            return object.__str__(self)
    __unicode__ = __str__


@interface.implementer(IPublishableContentPackageBundle)
class PublishableContentPackageBundle(PersistentContentPackageBundle,
                                      PublishableMixin):
    __external_can_create__ = True
    __external_class_name__ = 'ContentPackageBundle'

    mime_type = mimeType = PUBLISHABLE_BUNDLE_MIME_TYPE


_marker = object()


@interface.implementer(IContentPackageBundleLibrary)
class ContentPackageBundleLibrary(CheckingLastModifiedBTreeContainer):
    """
    BTree-based implementation of a bundle library.
    """

    __external_can_create__ = False

    def __repr__(self):
        try:
            return "<%s(%s, %s) at %s>" % (self.__class__.__name__,
                                           self.__name__,
                                           len(self),
                                           id(self))
        except ConnectionStateError:
            return object.__repr__(self)

    __str__ = __repr__
    __unicode__ = __str__

    @property
    def _parent_lib(self):
        return component.queryNextUtility(self, IContentPackageBundleLibrary)

    # Only these methods are expected to walk up the utility tree

    def get(self, key, default=None):
        obj = CheckingLastModifiedBTreeContainer.get(self, key, _marker)
        if obj is _marker:
            obj = default
            parent_lib = self._parent_lib
            if parent_lib is not None:
                obj = parent_lib.get(key, default)
        return obj

    def __getitem__(self, key):
        try:
            return CheckingLastModifiedBTreeContainer.__getitem__(self, key)
        except KeyError:
            parent_lib = self._parent_lib
            if parent_lib is None:
                raise

            return parent_lib[key]

    def add(self, bundle, event=True):
        if event:
            self[bundle.ntiid] = bundle
        else:
            self._setitemf(bundle.ntiid, bundle)
            locate(bundle, self, bundle.ntiid)
            self.updateLastMod()
    append = add

    def getBundles(self, parents=True):
        # recall that lower bundles override higher ones
        seen_ids = set()
        for k, v in self.items():
            seen_ids.add(k)
            yield v

        parent_lib = self._parent_lib
        if parent_lib is None or not parents:
            # done
            return

        for bundle in parent_lib.getBundles():
            if bundle.__name__ in seen_ids:
                continue
            seen_ids.add(bundle.__name__)
            yield bundle


#: The name of the file that identifies a directory
#: as a content bundle
_BUNDLE_META_NAME = "bundle_meta_info.json"
BUNDLE_META_NAME = _BUNDLE_META_NAME  # export

from zope.schema.fieldproperty import FieldProperty

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyKey
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IEnumerableDelimitedHierarchyBucket
from nti.contentlibrary.interfaces import ISyncableContentPackageBundleLibrary
from nti.contentlibrary.interfaces import ContentPackageBundleLibraryModifiedOnSyncEvent

from nti.contentlibrary.wref import contentunit_wref_to_missing_ntiid

from nti.ntiids.schema import ValidNTIID

from nti.schema.field import IndexedIterable


def get_package_for_bundle(package, library=None):
    """
    Returns a package suitable for storing in a :class:`IContentPackageBundle`
    given the package itself or it's ntiid.
    """
    if library is None:
        library = component.getUtility(IContentPackageLibrary)
    package_ntiid = getattr(package, 'ntiid', package)
    cp = library.get(package_ntiid)
    if cp:
        result = IWeakRef(cp)
    else:
        result = contentunit_wref_to_missing_ntiid(package_ntiid)
    return result


class IContentBundleMetaInfo(IContentPackageBundle):

    ContentPackages = IndexedIterable(
                        title=u"An iterable of NTIIDs of sub-containers embedded via reference in this content",
                        value_type=ValidNTIID(title=u"The embedded NTIID"),
                        unique=True,
                        default=())


_IContentBundleMetaInfo = IContentBundleMetaInfo  # alias


@EqHash('ntiid')
@NoPickle
@WithRepr
class ContentBundleMetaInfo(object):
    """
    Meta-information.

    Instead of creating fields and a schema, we will simply read
    in anything found in the json and store them in ourself.

    Validation and updating is delayed until a full adapting schema call
    can be used. The only exception is for the NTIIDs that make up
    content package references.
    """

    ContentPackages = FieldProperty(IContentBundleMetaInfo['ContentPackages'])

    _ContentPackages_wrefs = ()

    def __init__(self, key_or_source, content_library, require_ntiid=True):
        # For big/complex JSON, we want to avoid loading the JSON
        # and turning it indo objects unless the timestamp is newer;
        # however, here we need the NTIID, which comes out of the file;
        # also we expect it to be quite small
        if IDelimitedHierarchyKey.providedBy(key_or_source):
            json_value = key_or_source.readContentsAsJson()
        else:
            json_value = key_or_source

        # If there is no NTIID, we should derive one automatically
        # from the key name
        if require_ntiid and 'ntiid' not in json_value:
            raise MissingContentBundleNTIIDException("Missing ntiid",
                                                     key_or_source)

        for k, v in json_value.items():
            setattr(self, str(k), v)

        if IDelimitedHierarchyKey.providedBy(key_or_source):
            self.key = key_or_source
            self.createdTime = key_or_source.createdTime
            self.lastModified = key_or_source.lastModified
        else:
            self.key = None
            self.createdTime = self.lastModified = time.time()

        if self.ContentPackages:
            self._ContentPackages_wrefs = self.getContentPackagesWrefs(content_library)
            self.__dict__['ContentPackages'] = self._ContentPackages_wrefs

    def getContentPackagesWrefs(self, library):
        """
        persistent content bundles want to refer to weak refs;
        we read the meta as ntiid strings that we either resolve
        to actual packages (which we then weak ref, so that equality works out),
        or weak refs to missing ntiids
        """
        result = OOSet()
        for ntiid in self.ContentPackages or ():
            result.add(get_package_for_bundle(ntiid, library))
        return result
_ContentBundleMetaInfo = ContentBundleMetaInfo  # alias


from nti.contentlibrary.dublincore import DCMETA_FILENAME
from nti.contentlibrary.dublincore import read_dublincore_from_named_key

from nti.externalization.internalization import validate_named_field_value

from nti.zodb import readCurrent as _readCurrent


def synchronize_bundle_vendor_info(bundle, bucket):
    vendor_json_key = bucket.getChildNamed(VENDOR_INFO_NAME)
    vendor_info = IContentPackageBundleVendorInfo(bundle)
    if not vendor_json_key:
        vendor_info.clear()
        vendor_info.createdTime = 0
        vendor_info.lastModified = 0
    elif vendor_json_key.lastModified > vendor_info.lastModified:
        vendor_info.clear()
        vendor_info.update(vendor_json_key.readContentsAsJson())
        vendor_info.createdTime = vendor_json_key.createdTime
        vendor_info.lastModified = vendor_json_key.lastModified
        notify(ContentPackageBundleVendorInfoSynchronized(bundle))


def _are_package_refs_equal(a, b):
    if isinstance(a, OOSet) and isinstance(b, OOSet):
        return not bool(ooset_difference(a, b))
    elif isinstance(a, (set, tuple)) and isinstance(b, (set, tuple)):
        return a == b
    else:
        return set(a) == set(b)


def _set_bundle_packages(bundle, meta):
    """
    We need to be careful and not wipe any packages (IEditableContentPackages) that
    did not come through the sync process.
    """
    def cannot_remove(package):
        return IEditableContentPackage.providedBy(package)

    # pylint: disable=protected-access
    new_wrefs = list(meta._ContentPackages_wrefs)
    try:
        old_wrefs = set(bundle._ContentPackages_wrefs)
        for package_ref in bundle._ContentPackages_wrefs or ():
            package = package_ref()
            if cannot_remove(package):
                new_wrefs.append(package_ref)
    except AttributeError:
        packages = list(meta.ContentPackages)
        for package in bundle.ContentPackages or ():
            if cannot_remove(package):
                packages.append(package)
        bundle.ContentPackages = packages
    else:
        bundle._ContentPackages_wrefs = new_wrefs
        new_wrefs = set(new_wrefs)
        added = new_wrefs - old_wrefs
        removed = old_wrefs - new_wrefs
        logger.info('Modifying bundle packages (added=%s) (removed=%s)',
                    added, removed)


def synchronize_bundle(data_source, bundle,
                       content_library=None,
                       excluded_keys=(),
                       update_bundle=True,
                       _meta=None):
    """
    Given either a :class:`IDelimitedHierarchyKey` whose contents are a JSON
    or a JSON source, and an object representing a :class:`IContentPackageBundle`,
    synchronize the bundle fields (those declared in the interface) to match
    the JSON values.

    This is different from normal externalization/internalization in that
    it takes care not to set any fields whose values haven't changed.

    The bundle object will have its bundle-standard `root` property
    set to the ``data_source`` bucket.

    :keyword content_library: The implementation of :class:`IContentPackageLibrary`
            that should be used to produce the ContentPackage objects. These will be
            stored in the bundle as weak references, possibly to missing NTIIDs.
            The bundle implementation should either extend :class`PersistentContentPackageBundle`
            or provide its own setter implementation that deals with this.

            If you do not provide this utility, the currently active library will
            be used.
    """
    # we can't check the lastModified dates, the bundle object
    # might have been modified independently
    if content_library is None:
        content_library = component.getUtility(IContentPackageLibrary)

    bundle_iface = IContentPackageBundle
    # In the past, we used interface.providedBy(bundle), but that
    # could let anything be set
    meta = _meta or _ContentBundleMetaInfo(data_source,
                                           content_library,
                                           require_ntiid='ntiid' not in excluded_keys)
    fields_to_update = (
        set(meta.__dict__)
        - set(excluded_keys)
        - {'lastModified', 'createdTime', 'modified', 'created'}
    )

    # Be careful to only update fields that have changed
    modified = False
    for k in fields_to_update:
        # pylint: disable=no-value-for-parameter
        if not bundle_iface.get(k):
            # not an interface field, ignore
            continue
        if k == 'ContentPackages':
            # Treat these specially so that we don't have to resolve
            # weak references; if everything was *missing*, the ContentPackages
            # could come back as empty both places
            try:
                # pylint: disable=protected-access
                needs_copy = not _are_package_refs_equal(bundle._ContentPackages_wrefs,
                                                         meta._ContentPackages_wrefs)
            except AttributeError:
                needs_copy = getattr(bundle, k, None) != getattr(meta, k)
            if needs_copy:
                # Our ContentPackages actually may bypass the interface by already
                # being weakly referenced if missing, hence avoiding validation
                modified = True
                _set_bundle_packages(bundle, meta)
        elif getattr(bundle, k, None) != getattr(meta, k):
            modified = True
            validate_named_field_value(bundle, bundle_iface,
                                       str(k), getattr(meta, k))()

    if update_bundle and bundle.root != meta.key.__parent__:
        modified = True
        bundle.root = meta.key.__parent__

    if modified:
        bundle.updateLastMod(meta.lastModified)
    elif bundle.lastModified < meta.lastModified:
        bundle.updateLastModIfGreater(meta.lastModified)

    return modified


def sync_bundle_from_json_key(data_key, bundle,
                              content_library=None,
                              dc_meta_name=DCMETA_FILENAME,
                              excluded_keys=(),
                              dc_bucket=None,
                              update_bundle=True,
                              _meta=None):
    """
    :keyword dc_meta_name: If given (defaults to a standard value),
            DublinCore metadata will be read from this file (a sibling of the `data_key`).
            You can use a non-standard
            filename if you might have multiple things in the same bucket.
    """
    result = synchronize_bundle(data_key, bundle,
                                excluded_keys=excluded_keys,
                                update_bundle=update_bundle,
                                content_library=content_library,
                                _meta=_meta)
    # Metadata if we need it
    dc_bucket = data_key.__parent__ if dc_bucket is None else dc_bucket
    read_dublincore_from_named_key(bundle, dc_bucket, dc_meta_name)
    synchronize_bundle_vendor_info(bundle, dc_bucket)
    return result


@interface.implementer(ISyncableContentPackageBundleLibrary)
@component.adapter(IContentPackageBundleLibrary)
class _ContentPackageBundleLibrarySynchronizer(object):

    def __init__(self, context):
        self.context = context

    def syncFromBucket(self, bucket):
        """
        Sync anything we have on disk, without removing any bundles
        that may have been created through some API.
        """
        sm = component.getSiteManager(self.context)
        content_library = sm.getUtility(IContentPackageLibrary)
        _readCurrent(content_library)
        _readCurrent(self.context)

        bundle_meta_keys = list()

        for child in bucket.enumerateChildren():
            if not IEnumerableDelimitedHierarchyBucket.providedBy(child):
                # not a directory
                continue
            bundle_meta_key = child.getChildNamed(_BUNDLE_META_NAME)
            if not IDelimitedHierarchyKey.providedBy(bundle_meta_key):
                # Not a readable file
                continue
            bundle_meta_keys.append(bundle_meta_key)

        need_event = False

        bundle_metas = {_ContentBundleMetaInfo(k, content_library)
                        for k in bundle_meta_keys}
        # Now determine what to add/update.
        # Order matters here, very much.
        # The __contains__ operation for keys does not take parent
        # libraries into account, nor does iterating the keys; thus,
        # we're safe by checking the ntiids against our context.
        # By the time we look for things to update, we know we will
        # be accessing an item local in our context, not from parent,
        # even though __getitem__ is recursive.

        things_to_add = {
            x for x in bundle_metas if x.ntiid not in self.context
        }
        # Take those out
        bundle_metas = bundle_metas - things_to_add

        things_to_update = {x for x in bundle_metas
                            if x.lastModified > self.context[x.ntiid].lastModified}

        # All of these remaining things haven't changed,
        # but by definition must still be in the container
        bundle_metas = bundle_metas - things_to_update

        def _update_bundle(bundle, meta):
            sync_bundle_from_json_key(meta.key, bundle,
                                      content_library=content_library,
                                      # pass in the existing object as an
                                      # optimization
                                      _meta=meta)
            assert meta.ntiid == bundle.ntiid

        # Start with the adds
        if things_to_add:
            need_event = True
            logger.info("Adding bundles to library %s: %s",
                        self.context, things_to_add)
            for meta in things_to_add:
                bundle = PersistentContentPackageBundle()
                bundle.createdTime = meta.createdTime
                _update_bundle(bundle, meta)

                lifecycleevent.created(bundle)
                self.context[meta.ntiid] = bundle  # added

        # Now any updates
        if things_to_update:
            need_event = True
            logger.info("Updating bundles in library %s: %s",
                        self.context, things_to_update)
            for meta in things_to_update:
                bundle = self.context[meta.ntiid]
                _update_bundle(bundle, meta)
                # make update_bundle return the changed attributes?
                lifecycleevent.modified(bundle)

        if need_event:
            event = ContentPackageBundleLibraryModifiedOnSyncEvent(self.context)
            event.bucket = bucket
            notify(event)
        else:
            logger.info("Nothing to do to sync library %s",
                        self.context)
