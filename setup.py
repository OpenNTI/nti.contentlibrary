import codecs
from setuptools import setup, find_packages

entry_points = {
}

TESTS_REQUIRE = [
	'fudge',
	'nose2[coverage_plugin]',
	'nti.testing',
	'pyhamcrest',
	'z3c.baseregistry',
	'zope.testrunner',
]

def _read(fname):
	with codecs.open(fname, encoding='utf-8') as f:
		return f.read()

setup(
	name='nti.contentlibrary',
	version=_read('version.txt').strip(),
	author='Jason Madden',
	author_email='jason@nextthought.com',
	description="NTI contentlibrary",
	long_description=_read('README.rst'),
	license='Apache',
	keywords='contentlibrary',
	classifiers=[
		'Intended Audience :: Developers',
		'Natural Language :: English',
		'Operating System :: OS Independent',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.4',
		'Programming Language :: Python :: 3.5',
		'Programming Language :: Python :: Implementation :: CPython',
		'Programming Language :: Python :: Implementation :: PyPy',
	],
	zip_safe=True,
	packages=find_packages('src'),
	package_dir={'': 'src'},
	include_package_data=True,
	namespace_packages=['nti'],
	tests_require=TESTS_REQUIRE,
	install_requires=[
		'setuptools',
        'anyjson',
        'BTrees',
        'boto',
        'lxml',
        'nti.containers',
        'nti.contentfragments',
        'nti.contenttypes.presentation',
        'nti.coremetadata',
		'nti.externalization',
        'nti.ntiids',
        'nti.property',
        'nti.schema',
        'nti.site',
        'nti.traversal',
		'nti.wref',
        'nti.zodb',
        'persistent',
        'PyYAML',
        'repoze.lru',
        'zc.catalog',
        'ZODB',
		'zope.annotation',
        'zope.cachedescriptors',
		'zope.catalog',
		'zope.component',
        'zope.configuration',
		'zope.container',
		'zope.deprecation',
		'zope.dublincore',
        'zope.event',
		'zope.i18nmessageid',
		'zope.interface',
        'zope.intid',
		'zope.location',
        'zope.lifecycleevent',
		'zope.principalannotation',
        'zope.schema',
		'zope.security',
		'zope.site',
        'zope.traversing'
	],
	extras_require={
		'test': TESTS_REQUIRE,
	},
	entry_points=entry_points,
)