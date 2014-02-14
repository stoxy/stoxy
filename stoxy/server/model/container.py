from __future__ import absolute_import

from grokcore.component import context, implements
from zope import schema
from zope.component import provideSubscriptionAdapter
from zope.interface import Interface

from opennode.oms.model.model.actions import ActionsContainerExtension
from opennode.oms.model.model.base import Container
from opennode.oms.model.model.base import ContainerInjector
from opennode.oms.model.model.base import IDisplayName
from opennode.oms.model.model.base import ReadonlyContainer
from opennode.oms.model.model.byname import ByNameContainerExtension
from opennode.oms.model.model.root import OmsRoot
from opennode.oms.model.model.symlink import Symlink
from opennode.oms.zodb import db

from stoxy.server import common
from stoxy.server import model


class IInStorageContainer(Interface):
    """Implementors of this interface can be contained in a `StorageContainer` container."""


class IStorageContainer(Interface):
    oid = schema.TextLine(title=u"CDMI Object ID",
                          max_length=common.OBJECTID_MAX_BYTES * common.BASE16_SIZE_MULTIPLIER,
                          min_length=common.OBJECTID_MIN_BYTES * common.BASE16_SIZE_MULTIPLIER,
                          required=False)
    name = schema.TextLine(title=u"Container name", required=True)
    metadata = schema.Dict(title=u'Metadata', key_type=schema.TextLine(),
                           value_type=schema.TextLine(), required=False)


class IRootContainer(Interface):
    """Implementor of this interface is a root element of a sub-hierarchy"""


class StorageContainer(Container):
    implements(IStorageContainer, IDisplayName, IInStorageContainer)

    __contains__ = IInStorageContainer

    def __init__(self, oid=None, name=None, metadata={}):
        self.oid = unicode(common.generate_guid_b16() if oid is None else oid)
        self.__name__ = name
        self.metadata = metadata

    @property
    def name(self):
        return self.__name__

    def display_name(self):
        return self.name

    @property
    def nicknames(self):
        return [self.name]

    def __str__(self):
        return '<StorageContainer ObjectID=%s name=%s>' % (self.oid, self.name)

    @property
    def type(self):
        return StorageContainer


class ObjectIdContainer(ReadonlyContainer):
    implements(IInStorageContainer, IDisplayName)
    __contains__ = IInStorageContainer
    __name__ = 'cdmi_objectid'

    @property
    def name(self):
        return 'cdmi_objectid'

    def display_name(self):
        return self.name

    @property
    def nicknames(self):
        return [self.name]

    @property
    def _items(self):
        machines = db.get_root()['oms_root']['storage']

        computes = {}

        def collect(container):
            seen = set()
            for item in container.listcontent():
                if IStorageContainer.providedBy(item) or model.dataobject.IDataObject.providedBy(item):
                    computes[item.oid] = Symlink(item.oid, item)

                if IStorageContainer.providedBy(item) and item.oid not in seen:
                    seen.add(item.oid)
                    collect(item)

        collect(machines)
        return computes

    @property
    def oid(self):
        return self.__name__

    def __str__(self):
        return '<ObjectIDContainer>'

    @property
    def type(self):
        return StorageContainer


class RootStorageContainer(Container):
    implements(IStorageContainer, IDisplayName, IRootContainer)
    __contains__ = IInStorageContainer
    __name__ = 'storage'

    def __init__(self, *args, **kw):
        self.oid = unicode(common.generate_guid_b16())
        self.metadata = {}
        super(RootStorageContainer, self).__init__(*args, **kw)

    @property
    def name(self):
        return self.__name__

    def display_name(self):
        return self.name

    @property
    def nicknames(self):
        return [self.name]

    def __str__(self):
        return '<RootStorageContainer ObjectID=%s name=%s>' % (self.oid, self.name)

    @property
    def type(self):
        return RootStorageContainer


class DataObjectsRootInjector(ContainerInjector):
    context(OmsRoot)
    __class__ = RootStorageContainer


class ObjectIDContainerInjector(ContainerInjector):
    context(RootStorageContainer)
    __class__ = ObjectIdContainer


provideSubscriptionAdapter(ActionsContainerExtension, adapts=(RootStorageContainer, ))
provideSubscriptionAdapter(ByNameContainerExtension, adapts=(RootStorageContainer, ))

provideSubscriptionAdapter(ActionsContainerExtension, adapts=(StorageContainer, ))
provideSubscriptionAdapter(ByNameContainerExtension, adapts=(StorageContainer, ))
