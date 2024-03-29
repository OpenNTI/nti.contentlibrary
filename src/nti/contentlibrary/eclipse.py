#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Objects for working with Eclipse index representations of content packages.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# This module is badly named now

from lxml import etree

from six.moves import urllib_parse

from zope import interface

from nti.contentlibrary.dublincore import read_dublincore_from_named_key

from nti.contentlibrary.interfaces import ILegacyCourseConflatedContentPackage

from nti.ntiids.ntiids import is_valid_ntiid_string

###
# Constants for file names we know and care about
##
#: The main XML file found inside the content package, giving the
#: layout of the topics and sections.
TOC_FILENAME = u'eclipse-toc.xml'

#: A possibly-missing ZIP file containing the downloadable content.
ARCHIVE_FILENAME = u'archive.zip'

#: A glossary file applicable to the entire content.
#: .. todo:: In the future, if we need to, we can add a node property
#: for sub-glossaries specific to just portions of the content
MAIN_CSV_CONTENT_GLOSSARY_FILENAME = u'nti_content_glossary.csv'

_toc_item_attrs = ('NTIRelativeScrollHeight', 'label', 'ntiid', 'href')

# Note that we preserve href as a string, and manually
# set a 'key' property for BWC
_toc_item_key_attrs = ('icon', 'thumbnail')

logger = __import__('logging').getLogger(__name__)


def _node_get(node, name, default=None):
    # LXML defaults to returning ASCII attributes as byte strings
    # https://mailman-mail5.webfaction.com/pipermail/lxml/2011-December/006239.html
    val = node.get(name, default)
    if isinstance(val, bytes):
        val = val.decode('utf-8')
    return val


def _href_for_sibling_key(href):
    __traceback_info__ = href  # pylint: disable=unused-variable
    assert bool(href)
    assert not href.startswith('/')

    # Strip any fragment
    path = urllib_parse.urlparse(href).path
    path = path.decode('utf-8') if isinstance(path, bytes) else path

    # Just in case they send url-encoded things, decode them
    # (TODO: Should this be implementation dependent? S3 might need url-encoding?)
    # If so, probably the implementation of make_sibling_key should do that,
    # it takes a 'name'-domain

    # If we get a multi-segment path, we need to deconstruct it
    # into bucket parts to be sure that it externalizes
    # correctly.
    # pylint: disable=too-many-function-args
    parts = [urllib_parse.unquote(x) for x in path.split('/')]
    parts = [x.decode('utf-8') if isinstance(x, bytes) else x for x in parts]

    # NOTE: This implementation makes it impossible to have an actual / in a
    # href, even though they are technically legal in unix filenames
    path = u'/'.join(parts)
    return path


def _tocItem(node, toc_entry, factory=None, child_factory=None):
    tocItem = factory()
    # pylint: disable=protected-access
    tocItem._v_toc_node = node  # for testing and secret stuff
    for i in _toc_item_attrs:
        val = _node_get(node, i, i)
        if val and val is not i:
            setattr(tocItem, str(i), val)

    if node.get('sharedWith', ''):
        tocItem.sharedWith = _node_get(node, 'sharedWith').split(' ')

    # Now the things that should be keys.
    # NOTE: The href may have a fragment in it, but the key is supposed
    # to point to an actual 'file' on disk, so we strip the fragment
    # off (if there is one). Also, the hrefs may be URL encoded
    # if they contain spaces, and since we are in the domain of knowing
    # about URLs, it is our job to decode them.
    href = tocItem.href
    tocItem.key = toc_entry.make_sibling_key(_href_for_sibling_key(href))
    for i in _toc_item_key_attrs:
        val = _node_get(node, i)
        if val:
            # We leave it to the toc_entry to decide if/how
            # it needs to deal with multi-level keys, either
            # by creating a hierarchy of keys (filesystem)
            # or by simply string appending (boto)
            setattr(tocItem, str(i),
                    toc_entry.make_sibling_key(_href_for_sibling_key(val)))

    children = tocItem.children_iterable_factory()
    for ordinal, child in enumerate(node.iterchildren(tag='topic'), 1):
        child = _tocItem(child,
                         toc_entry,
                         factory=child_factory,
                         child_factory=child_factory)
        child.__parent__ = tocItem
        child.ordinal = ordinal
        child._v_toc_node = child  # for testing and secret stuff
        children.append(child)
    if children:
        tocItem.children = children

    embeddedContainerNTIIDs = list()
    for child in node.iterchildren(tag='object'):
        ntiid = _node_get(child, 'ntiid')
        if not ntiid:
            continue

        if not is_valid_ntiid_string(ntiid):
            continue

        if ntiid not in embeddedContainerNTIIDs:
            embeddedContainerNTIIDs.append(ntiid)

    if embeddedContainerNTIIDs:
        # pylint: disable=unused-variable
        __traceback_info__ = embeddedContainerNTIIDs
        tocItem.embeddedContainerNTIIDs = tuple(embeddedContainerNTIIDs)
    return tocItem

# Cache for content packages
# should be done at a higher level.


etree_Error = getattr(etree, 'Error')


def EclipseContentPackage(toc_entry,
                          package_factory=None,
                          unit_factory=None):
    """
    Given a :class:`nti.contentlibrary.interfaces.IDelimitedHierarchyEntry` pointing
    to an Eclipse TOC XML file, parse it and return the :class:`IContentPackage`
    tree.

    If parsing fails, returns None.

    If a TOC node contains a 'sharedWith' attribute, then it is a space separated string
    defining the default value that should be used for sharing within that content if
    no other preference is specified. (See :class:`nti.appserver.interfaces.IContentUnitPreferences`;
    an adapter should be registered.)

    :param toc_entry: The hierarchy entry we will use to read the XML from. We make certain
            assumptions about the hierarchy this tree came from, notably that it is only one level
            deep (or rather, it is at least two levels deep and we will be able to access it
            given just the parent entry). (TODO: That property should probably become an IDelimitedHierarchyEntry)
    :param package_factory: A callable of no arguments that produces an :class:`.interfaces.IContentPackage`
    :param unit_factory: A callable of no arguments that cooperates with the `package_factory` and produces
            :class:`.interfaces.IContentUnit` objects that can be part of the content package.
    """

    try:
        root = toc_entry.key.readContentsAsETree()
    except (IOError, etree_Error):
        logger.debug("Failed to parse TOC at %s", toc_entry, exc_info=True)
        return None

    toc_last_modified = toc_entry.lastModified
    content_package = _tocItem(root,
                               toc_entry,
                               factory=package_factory,
                               child_factory=unit_factory)
    # NOTE: assuming only one level of hierarchy (or at least the accessibility given just the parent)
    # root and index should probably be replaced with IDelimitedHierarchyEntry objects.
    # NOTE: IDelimitedHierarchyEntry is specified as '/' delimited. This means that when we are working with
    # filesystem objects we have path-dependencies. We won't work on windows
    content_package.root = toc_entry.get_parent_key()
    content_package.index = toc_entry.key
    content_package.index_last_modified = toc_last_modified

    toc_jsonp = TOC_FILENAME + '.jsonp'
    content_package.index_jsonp = toc_entry.does_sibling_entry_exist(toc_jsonp)

    renderVersion = root.get('renderVersion')
    if renderVersion:
        content_package.renderVersion = int(renderVersion)

    isCourse = root.get('isCourse')
    if isCourse is not None:
        as_str = str(isCourse).lower()
        if not isCourse:
            isCourse = False
        else:
            isCourse = as_str in ('1', 'true', 'yes', 'y', 't')
    if isCourse:
        interface.alsoProvides(content_package,
                               ILegacyCourseConflatedContentPackage)
        content_package.isCourse = isCourse
        courses = root.xpath('/toc/course')
        if not courses or len(courses) != 1:
            raise ValueError("Invalid course: 'isCourse' is true, "
                             "but wrong 'course' node")
        course = courses[0]
        courseTitle = _node_get(course, 'label')
        courseName = _node_get(course, 'courseName')

        content_package.courseName = courseName
        content_package.courseTitle = courseTitle

        # The newest renderings have an <info src="path_to_file.json" />
        # node in them. But older renderings may also have a file
        # just in their root called "course_info.json" (which in
        # practice is also always the value of info[@src].
        # Take whatever we can get.
        info = course.xpath('info')
        if info:  # sigh
            content_package.courseInfoSrc = _node_get(info[0], 'src')
        elif content_package.does_sibling_entry_exist('course_info.json'):
            content_package.courseInfoSrc = u'course_info.json'

    if content_package.does_sibling_entry_exist(ARCHIVE_FILENAME):
        content_package.archive = ARCHIVE_FILENAME
        content_package.installable = True
        content_package.archive_unit = \
            unit_factory(key=content_package.make_sibling_key(ARCHIVE_FILENAME),
                         href=ARCHIVE_FILENAME,
                         title=u'Content Archive')
        content_package.archive_unit.__parent__ = content_package

    read_dublincore_from_named_key(content_package, content_package.root)
    return content_package
