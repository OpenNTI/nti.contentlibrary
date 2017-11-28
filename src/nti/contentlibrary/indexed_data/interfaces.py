#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces representing the indexed data that can be attached to content units.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.interface.common.mapping import IReadMapping

TAG_NAMESPACE_FILE = 'nti.contentlibrary.indexed_data.NamespaceFile'


class IIndexedDataContainer(IReadMapping):
    """
    The indexed data for a content unit.

    These are expected to be accessed by adapting the content
    unit to this interface; there may be several different
    kinds or namespaces of indexed data associated with a
    content unit, in which case they would be named adapters.

    The actual contents of the indexed data items are not defined;
    however, they are required to be identified by ``ntiid``, and are
    typically represented as dictionaries.
    """

    ntiid = interface.Attribute("The NTIID of the content unit.")


class IAudioIndexedDataContainer(IIndexedDataContainer):
    """
    Special adapter, pre-namespaced for audio index data.
    """

IAudioIndexedDataContainer.setTaggedValue(TAG_NAMESPACE_FILE,
                                          'audio_index.json')


class IVideoIndexedDataContainer(IIndexedDataContainer):
    """
    Special adapter, pre-namespaced for video index data.
    """

IVideoIndexedDataContainer.setTaggedValue(TAG_NAMESPACE_FILE,
                                          'video_index.json')


class IRelatedContentIndexedDataContainer(IIndexedDataContainer):
    """
    Special adapter, pre-namespaced for related content index data.
    """

IRelatedContentIndexedDataContainer.setTaggedValue(TAG_NAMESPACE_FILE,
                                                   'related_content_index.json')


class ITimelineIndexedDataContainer(IIndexedDataContainer):
    """
    Special adapter, pre-namespaced for timeline data.
    """

ITimelineIndexedDataContainer.setTaggedValue(TAG_NAMESPACE_FILE,
                                             'timeline_index.json')


class ISlideDeckIndexedDataContainer(IIndexedDataContainer):
    """
    Special adapter, pre-namespaced for slidedeck data.
    """

ISlideDeckIndexedDataContainer.setTaggedValue(TAG_NAMESPACE_FILE,
                                              'slidedeck_index.json')

CONTAINER_IFACES = (IRelatedContentIndexedDataContainer,
                    ISlideDeckIndexedDataContainer,
                    ITimelineIndexedDataContainer,
                    IVideoIndexedDataContainer,
                    IAudioIndexedDataContainer)


class IContainedObjectCatalog(interface.Interface):
    """
    An index that maps contained objects to their containers.
    """

# BWC Exports


from nti.contenttypes.presentation.interfaces import ISiteAdapter
from nti.contenttypes.presentation.interfaces import INTIIDAdapter
from nti.contenttypes.presentation.interfaces import ITargetAdapter
from nti.contenttypes.presentation.interfaces import INamespaceAdapter
from nti.contenttypes.presentation.interfaces import ISlideDeckAdapter
from nti.contenttypes.presentation.interfaces import IContainersAdapter
from nti.contenttypes.presentation.interfaces import IContainedTypeAdapter

ISiteAdapter = ISiteAdapter
INTIIDAdapter = INTIIDAdapter
ITargetAdapter = ITargetAdapter
INamespaceAdapter = INamespaceAdapter
ISlideDeckAdapter = ISlideDeckAdapter
IContainersAdapter = IContainersAdapter
IContainedTypeAdapter = IContainedTypeAdapter
