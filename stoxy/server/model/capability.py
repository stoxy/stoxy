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

from stoxy.server import common


class ISystemCapability(Interface):
    oid = schema.TextLine(title=u"CDMI Object ID",
                          max_length=common.OBJECTID_MAX_BYTES * common.BASE16_SIZE_MULTIPLIER,
                          min_length=common.OBJECTID_MIN_BYTES * common.BASE16_SIZE_MULTIPLIER,
                          required=False)
    capabilities = schema.Dict(title=u'Capabilities', key_type=schema.TextLine(),
                           value_type=schema.TextLine(), required=False)


class SystemCapability(Container):
    implements(ISystemCapability, IDisplayName)

    __name__ = 'cdmi_capabilities'

    def __init__(self, *args, **kw):
        self.oid = unicode(common.generate_guid_b16())
        self.capabilities = {}
        super(SystemCapability, self).__init__(*args, **kw)

    @property
    def name(self):
        return self.__name__

    def display_name(self):
        return self.name

    @property
    def nicknames(self):
        return [self.name]

    def __str__(self):
        return '<Capability ObjectID=%s name=%s>' % (self.oid, self.name)

    @property
    def type(self):
        return SystemCapability


class DataObjectsRootInjector(ContainerInjector):
    context(OmsRoot)
    __class__ = SystemCapability
