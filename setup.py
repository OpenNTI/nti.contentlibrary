import codecs
from setuptools import setup, find_packages

entry_points = {
    'console_scripts': [
        "nti_s3put = nti.contentlibrary.nti_s3put:main",
    ]
}

TESTS_REQUIRE = [
    'fudge',
    'nti.testing',
    'zope.dottedname',
    'zope.formlib',
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
    description="NTI content library",
    long_description=_read('README.rst'),
    license='Apache',
    keywords='content library',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    url="https://github.com/NextThought/nti.contentlibrary",
    zip_safe=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    namespace_packages=['nti'],
    tests_require=TESTS_REQUIRE,
    install_requires=[
        'setuptools',
        'BTrees',
        'boto',
        'lxml',
        'nti.base',
        'nti.containers',
        'nti.contentfragments',
        'nti.contenttypes.presentation',
        'nti.coremetadata',
        'nti.dublincore',
        'nti.externalization',
        'nti.intid',
        'nti.mimetype',
        'nti.ntiids',
        'nti.property',
        'nti.publishing',
        'nti.recorder',
        'nti.schema',
        'nti.site',
        'nti.traversal',
        'nti.wref',
        'nti.zodb',
        'nti.zope_catalog',
        'persistent',
        'Pillow',
        'PyYAML',
        'repoze.lru',
        'six',
        'WebOb',
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
        'zope.traversing',
    ],
    extras_require={
        'test': TESTS_REQUIRE,
        'docs': [
            'Sphinx',
            'repoze.sphinx.autointerface',
            'sphinx_rtd_theme',
        ],
    },
    entry_points=entry_points,
)
