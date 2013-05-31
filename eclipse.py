#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Objects for working with Eclipse index representations of content packages.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# This module is badly named now

logger = __import__('logging').getLogger(__name__)

from lxml import etree

from zope.dublincore import xmlmetadata

###
## Constants for file names we know and care about
##
#: The main XML file found inside the content package, giving the
#: layout of the topics and sections.
TOC_FILENAME = 'eclipse-toc.xml'
#: A possibly-missing ZIP file containing the downloadable content.
ARCHIVE_FILENAME = 'archive.zip'
#: An optional XML file containing Dublin Core metadata to be associated
#: with the content package
DCMETA_FILENAME = 'dc_metadata.xml'
#: A glossary file applicable to the entire content.
#: .. todo:: In the future, if we need to, we can add a node property
#: for sub-glossaries specific to just portions of the content
MAIN_CSV_CONTENT_GLOSSARY_FILENAME = 'nti_content_glossary.csv'
#: Assessment items for this entire content
ASSESSMENT_INDEX_FILENAME = 'assessment_index.json'


_toc_item_attrs = ('NTIRelativeScrollHeight', 'href', 'icon', 'label', 'ntiid',)

def _node_get( node, name, default=None ):
	# LXML defaults to returning ASCII attributes as byte strings
	# https://mailman-mail5.webfaction.com/pipermail/lxml/2011-December/006239.html
	val = node.get( name, default )
	if isinstance(val, bytes):
		val = unicode(val, 'utf-8')
	return val

def _tocItem( node, toc_entry, factory=None, child_factory=None ):
	tocItem = factory()
	for i in _toc_item_attrs:
		setattr( tocItem, i, _node_get( node, i ) )

	if node.get( 'sharedWith', '' ):
		tocItem.sharedWith = _node_get( node, 'sharedWith' ).split( ' ' )

	tocItem.key = toc_entry.make_sibling_key( tocItem.href )

	children = []
	for ordinal, child in enumerate(node.iterchildren(tag='topic'), 1):
		child = _tocItem( child, toc_entry, factory=child_factory, child_factory=child_factory )
		child.__parent__ = tocItem
		child.ordinal = ordinal
		child._v_toc_node = child # for testing and secret stuff
		children.append( child )
	tocItem.children = children

	embeddedContainerNTIIDs = []
	for child in node.iterchildren(tag='object'):
		embeddedContainerNTIIDs.append( child.get('ntiid') )
	tocItem.embeddedContainerNTIIDs = embeddedContainerNTIIDs
	return tocItem

# Cache for content packages
# In basic profiling, the cache can provide 3X or more speedups,
# and dramatically reduces the variance
from repoze.lru import LRUCache
import zope.testing.cleanup
_cache = LRUCache( 1000 ) # TODO: Constant for the cache size
zope.testing.cleanup.addCleanUp( _cache.clear )

def EclipseContentPackage( toc_entry,
						   package_factory=None,
						   unit_factory=None ):
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
	:param package_factory: A callable of no arguments that produces an :class:`nti.contentlibrary.interfaces.IContentPackage`
	:param unit_factory: A callable of no arguments that cooperates with the `package_factory` and produces
		:class:`nti.contentlibrary.interfaces.IContentUnit` objects that can be part of the content package.
	"""

	try:
		toc_last_modified = toc_entry.lastModified
		content_package = _cache.get( toc_entry.key )
		if content_package is not None and content_package.index_last_modified <= toc_last_modified:
			return content_package

		try:
			root = etree.parse( toc_entry.filename ).getroot()
		except AttributeError:
			root = etree.fromstring( toc_entry.read_contents() )
	except (IOError,etree.Error):
		logger.debug( "Failed to parse TOC at %s", toc_entry, exc_info=True )
		return None

	content_package = _tocItem( root, toc_entry, factory=package_factory, child_factory=unit_factory )
	# NOTE: assuming only one level of hierarchy (or at least the accessibility given just the parent)
	# TODO: root and index should probably be replaced with IDelimitedHierarchyEntry objects.
	# NOTE: IDelimitedHierarchyEntry is specified as '/' delimited. This means that when we are working with
	# filesystem objects we have path-dependencies. We won't work on windows
	content_package.root = toc_entry.get_parent_key()
	content_package.index = toc_entry.key
	content_package.index_last_modified = toc_last_modified
	content_package.index_jsonp = toc_entry.does_sibling_entry_exist( TOC_FILENAME + '.jsonp' )

	renderVersion = root.get( 'renderVersion' )
	if renderVersion:
		content_package.renderVersion = int(renderVersion)

	if content_package.does_sibling_entry_exist( ARCHIVE_FILENAME ):
		content_package.archive = ARCHIVE_FILENAME
		content_package.installable = True
		content_package.archive_unit = unit_factory( key=content_package.make_sibling_key( ARCHIVE_FILENAME ),
													 href=ARCHIVE_FILENAME,
													 title='Content Archive' )
		content_package.archive_unit.__parent__ = content_package

	dcmetafile_contents = content_package.read_contents_of_sibling_entry( DCMETA_FILENAME )
	if dcmetafile_contents:
		metadata = xmlmetadata.parseString( dcmetafile_contents )
		if 'Creator' in metadata:
			content_package.creators = metadata['Creator']

	_cache.put( toc_entry.key, content_package )

	return content_package
