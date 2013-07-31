from __future__ import absolute_import

from grokcore.component import context, implements
from zope import schema
from zope.component import provideSubscriptionAdapter
from zope.interface import Interface

from opennode.oms.model.model.actions import ActionsContainerExtension
from opennode.oms.model.model.base import Container
from opennode.oms.model.model.base import ContainerInjector
from opennode.oms.model.model.base import IDisplayName
from opennode.oms.model.model.byname import ByNameContainerExtension
from opennode.oms.model.model.root import OmsRoot

from stoxy.server.common import generate_guid_b16


class IInStorageContainer(Interface):
    """Implementors of this interface can be contained in a `StorageContainer` container."""


class IStorageContainer(Interface):
    oid = schema.TextLine(title=u"CDMI Object ID", max_length=40, min_length=24, required=True)
    name = schema.TextLine(title=u"Container name", required=True)


class IRootContainer(Interface):
    """Implementor of this interface is a root element of a sub-hierarchy"""


class StorageContainer(Container):
    implements(IStorageContainer, IDisplayName, IInStorageContainer)

    __contains__ = IInStorageContainer

    def __init__(self, oid=None, name=None):
        self.oid = generate_guid_b16() if oid is None else oid
        self.__name__ = name

    @property
    def name(self):
        return self.__name__

    def display_name(self):
        return self.name

    @property
    def nicknames(self):
        return [self.name]


class RootStorageContainer(Container):
    implements(IStorageContainer, IRootContainer)
    __contains__ = IInStorageContainer
    __name__ = 'storage'

    def __init__(self, *args, **kw):
        self.oid = generate_guid_b16()
        super(RootStorageContainer, self).__init__(*args, **kw)

    @property
    def name(self):
        return self.__name__

    def __str__(self):
        return 'Root storage container'


class DataObjectsRootInjector(ContainerInjector):
    context(OmsRoot)
    __class__ = RootStorageContainer


provideSubscriptionAdapter(ActionsContainerExtension, adapts=(RootStorageContainer, ))
provideSubscriptionAdapter(ByNameContainerExtension, adapts=(RootStorageContainer, ))

provideSubscriptionAdapter(ActionsContainerExtension, adapts=(StorageContainer, ))
provideSubscriptionAdapter(ByNameContainerExtension, adapts=(StorageContainer, ))
