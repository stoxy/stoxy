from __future__ import absolute_import

from grokcore.component import implements
from zope import schema
from zope.interface import Interface

from opennode.oms.model.model.base import IDisplayName
from opennode.oms.model.model.base import Model

from stoxy.server.common import generate_guid_b16
from stoxy.server.model.container import IInStorageContainer


class IDataObject(Interface):
    oid = schema.TextLine(title=u"CDMI Object ID", max_length=40, min_length=24, required=True)
    name = schema.TextLine(title=u"Data object name", required=True)
    mimetype = schema.TextLine(title=u"MIME type of the data", required=True)
    value = schema.TextLine(title=u"Value URI", required=True)


class DataObject(Model):
    implements(IDataObject, IDisplayName, IInStorageContainer)

    def __init__(self, oid=None, name=None, mimetype=None, value=None):
        self.oid = generate_guid_b16() if oid is None else oid
        self.__name__ = name
        self.mimetype = mimetype
        self.value = value

    @property
    def name(self):
        return self.__name__

    def display_name(self):
        return self.name

    @property
    def nicknames(self):
        return [self.name, self.mimetype]
