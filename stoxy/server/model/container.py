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


class IInDataContainer(Interface):
    """Implementors of this interface can be contained in a `DataContainer` container."""


class IDataContainer(Interface):
    name = schema.TextLine(title=u"Container name", required=False)


class DataContainer(Container):
    implements(IDataContainer, IDisplayName, IInDataContainer)

    __contains__ = IInDataContainer

    def __init__(self, name):
        self.name = name

    def display_name(self):
        return self.name

    @property
    def nicknames(self):
        return [self.name]


class RootDataContainers(Container):
    __contains__ = IInDataContainer
    __name__ = 'storage'

    def __init__(self, *args, **kw):
        super(RootDataContainers, self).__init__(*args, **kw)

    def __str__(self):
        return 'Data container'


class DataObjectsRootInjector(ContainerInjector):
    context(OmsRoot)
    __class__ = RootDataContainers


provideSubscriptionAdapter(ActionsContainerExtension, adapts=(RootDataContainers, ))
provideSubscriptionAdapter(ByNameContainerExtension, adapts=(RootDataContainers, ))

provideSubscriptionAdapter(ActionsContainerExtension, adapts=(DataContainer, ))
provideSubscriptionAdapter(ByNameContainerExtension, adapts=(DataContainer, ))
