#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.container.contained import Contained

from z3c.autoinclude.zcml import includePluginsDirective

from nti.async.utils.processor import Processor

from nti.dataserver.utils.base_script import create_context

from nti.contentlibrary.render import QUEUE_NAMES


class PluginPoint(Contained):

    def __init__(self, name):
        self.__name__ = name

PP_CONTENTLIBRARY = PluginPoint('nti.contentlibrary')


class Constructor(Processor):

    def set_log_formatter(self, args):
        super(Constructor, self).set_log_formatter(args)

    def extend_context(self, context):
        includePluginsDirective(context, PP_CONTENTLIBRARY)

    def create_context(self, env_dir):
        context = create_context(env_dir, with_library=True,
                                 plugins=False,
                                 slugs=True,
                                 slugs_files=("*content_render.zcml", "*features.zcml"))
        self.extend_context(context)
        return context

    def conf_packages(self):
        return (self.conf_package, 'nti.app.contentlibrary', 'nti.async')

    def process_args(self, args):
        setattr(args, 'redis', True)
        setattr(args, 'library', True)
        setattr(args, 'queue_names', QUEUE_NAMES)
        super(Constructor, self).process_args(args)


def main():
    return Constructor()()

if __name__ == '__main__':
    main()
