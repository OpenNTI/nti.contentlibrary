#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for externalizing portions of the library.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six
import numbers
import collections
from six.moves import urllib_parse

import simplejson as json

from zope import component
from zope import interface

from nti.contentlibrary.interfaces import IS3Key
from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IFilesystemKey
from nti.contentlibrary.interfaces import IS3ContentUnit
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentRendered
from nti.contentlibrary.interfaces import IFilesystemBucket
from nti.contentlibrary.interfaces import IRequestSiteNames
from nti.contentlibrary.interfaces import IContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IContentUnitHrefMapper
from nti.contentlibrary.interfaces import IDelimitedHierarchyKey
from nti.contentlibrary.interfaces import IFilesystemContentUnit
from nti.contentlibrary.interfaces import IEditableContentPackage
from nti.contentlibrary.interfaces import IRenderableContentPackage
from nti.contentlibrary.interfaces import IAbsoluteContentUnitHrefMapper
from nti.contentlibrary.interfaces import IPublishableContentPackageBundle
from nti.contentlibrary.interfaces import ILegacyCourseConflatedContentPackage
from nti.contentlibrary.interfaces import IDisplayablePlatformPresentationResources

from nti.contentlibrary.utils import operate_encode_content

from nti.contentlibrary.wref import contentunit_wref_to_missing_ntiid

from nti.externalization.interfaces import IExternalObject
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.externalization import toExternalObject
from nti.externalization.externalization import to_standard_external_dictionary

from nti.mimetype.externalization import decorateMimeType

from nti.wref.interfaces import IWeakRef

MIMETYPE = StandardExternalFields.MIMETYPE
LAST_MODIFIED = StandardExternalFields.LAST_MODIFIED

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IExternalObject)
@component.adapter(IContentPackageLibrary)
class _ContentPackageLibraryExternal(object):

    def __init__(self, library):
        self.library = library

    def toExternalObject(self):
        return LocatedExternalDict({
            'title': "Library",
            'titles': [toExternalObject(x) for x in self.library.contentPackages or ()]
        })


def _path_maybe_quote(path):
    if ' ' in path:
        # Generally, we don't want to quote the path portion: it should already
        # have been quoted with the TOC file was written. However, for
        # hand-edited TOCs, it is convenient if we do quote it.
        path = urllib_parse.quote(path)
    return path


def _path_join(root_url, path=''):
    if path is None:
        return None
    path = _path_maybe_quote(path)
    return urllib_parse.urljoin(root_url, path)


def _root_url_of_key(key):
    href = IContentUnitHrefMapper(key).href
    # trailing slash is important for urljoin
    return href + ('' if href.endswith('/') else '/')


def _root_url_of_unit(unit):
    try:
        parent_key = unit.get_parent_key()
        return _root_url_of_key(parent_key) if parent_key else None
    except AttributeError:
        return None
root_url_of_unit = _root_url_of_unit

# This file, if present, will be read to gain a dictionary
# of presentation properties to be attached to the external
# representation of a content package (in the ``PresentationProperties`` key).
# We take little interest in the keys and values found here,
# simply requiring the keys to be strings; however, we do
# list some well-known keys and their corresponding values
# (when a dot is used, it means the key nested inside the containing dictionary):
#
# ``numbering``
#          A dictionary that controls the presentation of "chapter numbers" and "section numbers"
# ``numbering.suppressed``
#         A boolean; if `True`, then the user interface should not attempt to
#         add and display automatic numbering information (default is False, and the UI should display
#         automatic numbering).
# ``numbering.type``
#         A one character string as in HTML (1, a, A, i, I) giving the type of marker to use
#         for automatic numbering (for decimal numbers, lowercase alphabetic, uppercase alphabetic,
#         and lower and upper Roman, respectively); the default is 1
# ``numbering.start``
#         An integer giving the starting number; defaults to 1.
# ``numbering.separator``
#         A string giving the value to put between levels in the tree when autonumbering
#         a complete path. Defaults to '.'
# ``toc``
#          A dictionary that controls the presentation of various table of contents menus.
# ``toc.max-level``
#         An integer giving the maximum level to show in toc menus; defaults to all levels.
#
DEFAULT_PRESENTATION_PROPERTIES_FILE = 'nti_default_presentation_properties.json'


@interface.implementer(IExternalObject)
@component.adapter(IContentPackage)
class _ContentPackageExternal(object):

    def __init__(self, package):
        self.package = package

    def toExternalObject(self, **kwargs):
        result = to_standard_external_dictionary(self.package, **kwargs)
        result.__name__ = self.package.__name__
        result.__parent__ = self.package.__parent__

        root_url = _root_url_of_unit(self.package)
        # pylint: disable=protected-access
        result._root_url = root_url

        icon = self.package.icon
        if IDelimitedHierarchyKey.providedBy(icon):
            result['icon'] = IContentUnitHrefMapper(icon).href
        elif isinstance(icon, six.string_types):
            result['icon'] = icon

        mapper = IContentUnitHrefMapper(self.package.key, None)
        result['href'] = mapper.href if mapper else None

        result['root'] = root_url
        result['title'] = self.package.title  # Matches result['DCTitle']

        index_dc = ''
        if self.package.index_last_modified \
                and self.package.index_last_modified > 0:
            index_dc = '?dc=' + str(self.package.index_last_modified)

        index = self.package.index
        if index:
            result['index'] = IContentUnitHrefMapper(index).href + index_dc
        else:
            result['index'] = None

        jsonp = self.package.index_jsonp
        if jsonp:
            result['index_jsonp'] = IContentUnitHrefMapper(jsonp).href
        else:
            result['index_jsonp'] = None

        result['renderVersion'] = self.package.renderVersion
        result[StandardExternalFields.NTIID] = self.package.ntiid

        result['installable'] = self.package.installable
        if self.package.installable and self.package.archive_unit:
            a_unit = self.package.archive_unit
            result['archive'] = IContentUnitHrefMapper(a_unit).href
            result['Archive Last Modified'] = a_unit.lastModified

        # Attach presentation properties. This is here for several reasons:
        # - This information is not normative, not used by the server,
        #    and thus not part of the IContentPackage interface;
        # - We are moving toward having IContentPackages be dynamic and constructed
        #  from sub-parts of other IContentPackages; if this were a static part of the IContentPackage,
        #  extracted from eclipse-toc.xml, such information would get lost when nodes are used
        #  outside their original context;
        # - We can imagine supplying different presentation information to different clients;
        # this is easy to do by registering decorators for
        # (IContentPackage,IRequest)

        presentation_properties_cache_name = '_v_presentation_properties'
        presentation_properties = getattr(self.package,
                                          presentation_properties_cache_name,
                                          None)
        if presentation_properties is None:
            presentation_properties = {}
            try:
                name = DEFAULT_PRESENTATION_PROPERTIES_FILE
                try:
                    ext_data = self.package.read_contents_of_sibling_entry(name)
                except AttributeError:
                    ext_data = None
            except self.package.TRANSIENT_EXCEPTIONS:
                ext_data = None
                presentation_properties = None  # So we retry next time
            if ext_data:
                presentation_properties = json.loads(ext_data)
                assert isinstance(presentation_properties, collections.Mapping)
                for k in presentation_properties:
                    assert isinstance(k, six.string_types)

            setattr(self.package,
                    presentation_properties_cache_name,
                    presentation_properties)

        result['PresentationProperties'] = presentation_properties
        ppr = self.package.PlatformPresentationResources
        if ppr is not None:
            result['PlatformPresentationResources'] = toExternalObject(ppr)
        return result


@component.adapter(ILegacyCourseConflatedContentPackage)
class _LegacyCourseConflatedContentPackageExternal(_ContentPackageExternal):

    def toExternalObject(self, **kwargs):
        result = super(_LegacyCourseConflatedContentPackageExternal, self).toExternalObject(**kwargs)
        result['isCourse'] = self.package.isCourse
        result['courseName'] = self.package.courseName
        result['courseTitle'] = self.package.courseTitle
        return result


@component.adapter(IEditableContentPackage)
class EditableContentPackageExternal(_ContentPackageExternal):

    def _remove_empty(self, result):
        for name in list(result.keys()):
            value = result.get(name)
            if not value and not isinstance(value, numbers.Number):
                result.pop(name, None)
        return result

    def _is_published(self):
        return self.package.is_published()

    def toExternalObject(self, **kwargs):
        result = super(_EditableContentPackageExternal, self).toExternalObject(**kwargs)
        is_published = self._is_published()
        # remove anything empty
        if not is_published:
            self._remove_empty(result)
        # add locking/publishing
        result['isPublished'] = is_published
        result['version'] = self.package.version
        result['isLocked'] = self.package.is_locked()
        result['description'] = self.package.description
        result['indexLastModified'] = self.package.index_last_modified
        result['publishLastModified'] = self.package.publishLastModified
        return result
_EditableContentPackageExternal = EditableContentPackageExternal


@component.adapter(IRenderableContentPackage)
class _RenderableContentPackageExternal(_EditableContentPackageExternal):

    def _is_published(self):
        # Only display as published if also rendered
        return self.package.is_published() \
           and IContentRendered.providedBy(self.package)


@component.adapter(IEditableContentPackage)
class _ContentPackageExporter(_ContentPackageExternal):
    pass


@component.adapter(IEditableContentPackage)
class _EditableContentPackageExporter(_EditableContentPackageExternal):

    def get_externals(self, externals=None):
        return dict() if externals is None else externals

    def toExternalObject(self, externals=None, **kwargs):  # pylint: disable=arguments-differ
        result = super(_EditableContentPackageExporter, self).toExternalObject(**kwargs)
        contents = self.package.contents or b''
        data = operate_encode_content(contents,
                                      self.package,
                                      **self.get_externals(externals))
        result['contents'] = data
        result['contentType'] = self.package.contentType
        # remove unrequired
        for name in ('href', 'root', 'index', 'archive', 'index_jsonp',
                     'installable', 'renderVersion', 'PresentationProperties',
                     'PlatformPresentationResources', 'version',
                     'indexLastModified', 'publishLastModified'):
            result.pop(name, None)
        # standard fields
        if MIMETYPE not in result:
            result[MIMETYPE] = decorateMimeType(self.package, result)
        result[LAST_MODIFIED] = self.package.lastModified
        return result


@component.adapter(IContentPackageBundle)
class ContentBundleIO(InterfaceObjectIO):

    _ext_iface_upper_bound = IContentPackageBundle

    _excluded_in_ivars_ = getattr(InterfaceObjectIO,'_excluded_in_ivars_').union(
        {'root', 'PlatformPresentationResources', 'ContentPackages',
         'contributors', 'subjects', 'creators'}
    )

    validate_packages = True

    def toExternalObject(self, *args, **kwargs):  # pylint: disable=arguments-differ
        result = InterfaceObjectIO.toExternalObject(self, *args, **kwargs)
        if self._ext_self.root is not None:
            root_url = _root_url_of_key(self._ext_self.root)
            # pylint: disable=protected-access
            result._root_url = root_url
            result['root'] = root_url
        return result

    @classmethod
    def resolve(cls, ntiid, library):
        paths = library.pathToNTIID(ntiid) if library is not None else None
        return paths[0] if paths else None

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        items = parsed.pop('ContentPackages', None) or parsed.pop('Items', None)
        if parsed:
            result = InterfaceObjectIO.updateFromExternalObject(self, parsed)
        else:
            result = False
        library = component.queryUtility(IContentPackageLibrary)
        if items is not None: # empty is allowed
            packages = []
            for context in items:
                if IContentUnit.providedBy(context):
                    package = IWeakRef(context)
                else:
                    package = self.resolve(context, library)
                    if self.validate_packages and package is None:
                        raise KeyError("Cannot find content package", context)
                    else:
                        package = contentunit_wref_to_missing_ntiid(context)
                packages.append(package)
            self._ext_self.ContentPackages = packages
            result = True
        return result
_ContentBundleIO = ContentBundleIO


@component.adapter(IPublishableContentPackageBundle)
class PublishableContentBundleIO(ContentBundleIO):
    _ext_iface_upper_bound = IPublishableContentPackageBundle

_PublishableContentBundleIO = PublishableContentBundleIO


@component.adapter(IDisplayablePlatformPresentationResources)
class _DisplayablePlatformPresentationResourcesIO(InterfaceObjectIO):

    _ext_iface_upper_bound = IDisplayablePlatformPresentationResources

    def toExternalObject(self, *args, **kwargs):  # pylint: disable=arguments-differ
        result = InterfaceObjectIO.toExternalObject(self, *args, **kwargs)
        root_url = _root_url_of_key(self._ext_self.root)
        root_url = _path_maybe_quote(root_url)
        # pylint: disable=protected-access
        result._root_url = root_url
        result['href'] = root_url
        return result

    def updateFromExternalObject(self, *args, **kwargs):  # pylint: disable=arguments-differ
        raise NotImplementedError()


# key/path-to-URL-mapping


@interface.implementer(IContentUnitHrefMapper)
@component.adapter(IFilesystemContentUnit)
class _FilesystemContentUnitHrefMapper(object):
    href = None

    def __init__(self, unit):
        key = unit.key
        if key.bucket and unit.href:
            # the href is relative to the bucket, and may contain
            # a fragment
            bucket_href = IContentUnitHrefMapper(key.bucket).href
            self.href = _path_join(bucket_href, unit.href)
        else:
            # This shouldn't be hit?
            self.href = IContentUnitHrefMapper(key).href


from zope.location.interfaces import IRoot
from zope.location.location import LocationIterator

from zope.traversing.api import joinPath


@interface.implementer(IContentUnitHrefMapper)
@component.adapter(IFilesystemKey)
class _FilesystemKeyHrefMapper(object):

    href = None

    def __init__(self, key):
        parent_path = IContentUnitHrefMapper(key.bucket).href
        self.href = _path_join(parent_path, key.name)


@interface.implementer(IContentUnitHrefMapper)
@component.adapter(IFilesystemBucket)
class _FilesystemBucketHrefMapper(object):

    href = None

    @staticmethod
    def _url_prefix_of(p):
        if hasattr(p, 'url_prefix'):
            if p.url_prefix:
                # can't have empty segments in the path;
                # also, the leading '/' if any, is assumed
                name = p.url_prefix
                if name.startswith('/'):
                    name = name[1:]
                if name.endswith('/'):
                    name = name[:-1]
                return name

    def __init__(self, bucket):
        parents = []
        for p in LocationIterator(bucket):
            if hasattr(p, 'url_prefix'):
                pfx = self._url_prefix_of(p)
                if pfx:
                    parents.append(pfx)
                break

            if      hasattr(p, 'parent_enumeration') \
                and p.parent_enumeration is not None:
                # Tight coupling. We're passing here into
                # the layers of libraries and how they are set up.
                # We expect a relationship like this:
                # GlobalLibrary/
                # GlobalEnumeration
                #  p (this enumeration)
                #     bucket/...
                # This path is only partly tested in this code base,
                # but see nti.app.products.courseware.tests.test_workspaces
                # 1): Test this case in this code base.
                # Ideally we can do something more elegant, maybe implement
                # ILocationInfo?
                parents.append(p.root.__name__)
                global_lib = p.parent_enumeration.__parent__
                pfx = self._url_prefix_of(global_lib)
                if pfx:
                    parents.append(pfx)
                break

            if IRoot.providedBy(p):
                break

            if p.__name__:
                parents.append(p.__name__)

        self.href = joinPath('/', *reversed(parents))

        # since it's a bucket, we should end with a '/'
        # so urljoin works as expected
        if not self.href.endswith('/'):
            self.href += '/'


@interface.implementer(IAbsoluteContentUnitHrefMapper)
@component.adapter(IS3ContentUnit)
class _S3ContentUnitHrefMapper(object):

    href = None

    def __init__(self, unit):
        self.href = IContentUnitHrefMapper(unit.key).href


@interface.implementer(IAbsoluteContentUnitHrefMapper)
@component.adapter(IS3Key)
class _S3KeyHrefMapper(object):
    """
    Produces HTTP URLs for keys in buckets.    Takes steps to work with CORS
    and other distribution strategies.

    Use this mapper when the bucket name is a DNS name, and the bucket name
    also has a DNS CNAME set up for it, and the application accessing the content
    was served from the same CNAME origin (or doesn't care about cross-origin concerns).
    """
    href = None

    def __init__(self, key):
        # We have to force HTTP here, because using https (or protocol relative)
        # falls down for the browser: the certs on the CNAME we redirect to, *.s3.aws.amazon.com
        # don't match for bucket.name host
        request_sites = component.queryUtility(IRequestSiteNames)
        sites = request_sites.sites() if request_sites is not None else None
        if sites:
            # In the CORS case, we may be coming from an origin, to the dataserver
            # and serving content which ought to come back from the origin CDN. We cannot use
            # the request.host (Host) header, because that would name the dataserver, which
            # might not be the content origin. The preferred sites send back the
            # origin first
            self.href = 'http://' + sites[0] + '/' + key.key
        else:
            if request_sites is None:
                quoted_key = _path_maybe_quote(key.key)
            else:
                quoted_key = key.key
            self.href = 'http://' + key.bucket.name + '/' + quoted_key


@interface.implementer(IAbsoluteContentUnitHrefMapper)
class CDNS3KeyHrefMapper(object):
    """
    Produces protocol-relative URLs for keys in S3 buckets.

    Use this mapper when the content in a bucket is configured to be accessible
    at a specific address, typically in a CDN distribution. This mapper returns
    protocol relative addresses because the CDN address is assumed to be
    its own CNAME and equipped with certificates.
    """
    href = None

    def __init__(self, key, cdn_cname):
        """
        :param string cdn_name: The FQDN where the request should be directed.
        """
        self.href = '//' + cdn_cname + '/' + _path_maybe_quote(key.key)


class CDNS3KeyHrefMapperFactory(object):
    """
    A factory to produce :class:`CDNS3KeyHrefMapper` objects. Register
    this object (usually in code) as an adapter for S3 content objects,
    knowing the given name of the CDN distribution.
    """

    def __init__(self, cdn_name):
        self.cdn_name = cdn_name

    def __call__(self, key):
        return CDNS3KeyHrefMapper(key, self.cdn_name)


def map_all_buckets_to(cdn_name, _global=True):
    """
    WARNING: This API has global effects. Use
    with extreme caution.
    """
    if _global:
        site_man = component.getGlobalSiteManager()
    else:
        site_man = component.getSiteManager()

    # manually clear any previous registration
    site_man.unregisterAdapter(required=(IS3Key,),
                               provided=IAbsoluteContentUnitHrefMapper)
    # Note that we only need to register for the key, as the IS3ContentUnit mapper
    # simply maps the unit's key
    site_man.registerAdapter(CDNS3KeyHrefMapperFactory(cdn_name),
                             required=(IS3Key,),
                             provided=IAbsoluteContentUnitHrefMapper)
