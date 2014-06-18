#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not as does_not
from hamcrest import none
from hamcrest import has_property
from hamcrest import contains
from hamcrest import greater_than
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import has_key

from nti.testing.matchers import verifiably_provides
from nti.testing.matchers import validly_provides

from nti.contentlibrary import interfaces, filesystem

import nti.externalization
import nti.externalization.externalization
from nti.externalization.externalization import to_external_object

import anyjson as json
import os.path

from . import ContentlibraryLayerTest

from six.moves import cPickle as pickle

class TestFilesystemContentUnit(ContentlibraryLayerTest):


	def test_filesystem_content_interfaces(self):

		unit = filesystem.FilesystemContentPackage(
			filename='prealgebra/index.html',
			href = 'index.html',
			#root = 'prealgebra',
			#icon = 'icons/The%20Icon.png'
		)

		assert_that( unit, verifiably_provides( interfaces.IFilesystemContentPackage ) )




	def test_from_filesystem(self):

		package = filesystem._package_factory( os.path.join( os.path.dirname( __file__ ),
															 'TestFilesystem' ) )
		assert_that( package.key,
					 validly_provides( interfaces.IDelimitedHierarchyKey ) )

		assert_that( package,
					 validly_provides( interfaces.IFilesystemContentPackage ) )
		assert_that( package.creators, is_( ('Jason',) ) )
		assert_that( package.children[-1].children[-1],
					 has_property( 'embeddedContainerNTIIDs',
								   contains('tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1') ) )

		# package pickles ok
#		assert_that( pickle.loads(pickle.dumps(package)),
#					 is_(package))

		ext_package = to_external_object( package )
		assert_that( ext_package, has_entry( 'DCCreator', ('Jason',) ) )
		assert_that( ext_package, has_entry( 'Creator', 'Jason') )
		assert_that( ext_package, has_entry( 'PresentationProperties',
											 is_( { 'numbering': {'suppressed': False,
																  'type': 'I',
																  'start': 5,
																  'separator': '.' } } ) ) )
		assert_that( ext_package, does_not( has_key( 'isCourse' ) ) )
		assert_that( ext_package, does_not( validly_provides( interfaces.ILegacyCourseConflatedContentPackage ) ) )

		json.loads( json.dumps( ext_package ) ) # Round trips through JSON

	def test_library(self):
		library = filesystem.EnumerateOnceFilesystemLibrary( os.path.dirname(__file__) )
		assert_that( library, has_property( 'lastModified', greater_than( 0 ) ) )

		embed_paths = library.pathsToEmbeddedNTIID('tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1')
		assert_that( embed_paths, has_length( 1 ) )
		assert_that( embed_paths[0], has_length( 3 ) )
		assert_that( embed_paths[0][-1], has_property( 'ntiid', 'tag:nextthought.com,2011-10:USSC-HTML-Cohen.28' ) )

		pack_ext = to_external_object( library[0] )
		assert_that( pack_ext, has_entry( 'href', '/TestFilesystem/index.html' ) )

		library.url_prefix = '/SomePrefix/'

		pack_ext = to_external_object( library[0] )
		assert_that( pack_ext, has_entry( 'href', '/SomePrefix/TestFilesystem/index.html' ) )
		assert_that( pack_ext, has_entry( 'root', '/SomePrefix/TestFilesystem/' ) )

from nti.app.testing.layers import AppTestLayer

class TestAppFilesystem(ContentlibraryLayerTest):
	layer = AppTestLayer

	def test_adapter_prefs(self):
		# TODO: This test does not really belong here
		import zope.dottedname.resolve as dottedname
		IPrefs = dottedname.resolve( 'nti.appserver.interfaces.IContentUnitPreferences' )

		unit = filesystem.FilesystemContentPackage(
			filename='prealgebra/index.html',
			href = 'index.html',
			#root = 'prealgebra',
			#icon = 'icons/The%20Icon.png'
		)

		assert_that( IPrefs( unit, None ), is_( none() ) )

		unit.sharedWith = ['foo']

		assert_that( IPrefs( unit ), verifiably_provides( IPrefs ) )
		assert_that( IPrefs( unit ), has_property( '__parent__', unit ) )
