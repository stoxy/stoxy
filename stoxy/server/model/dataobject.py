from __future__ import absolute_import

from grokcore.component import implements
from zope import schema
from zope.interface import Interface

from opennode.oms.model.model.base import IDisplayName
from opennode.oms.model.model.base import Model

from stoxy.server.model.container import IInDataContainer


class IDataObject(Interface):
    name = schema.TextLine(title=u"Data object name", required=True)
    mimetype = schema.TextLine(title=u"MIME type of the data", required=True)
    value = schema.TextLine(title=u"Value URI", required=True)


class DataObject(Model):
    implements(IDataObject, IDisplayName, IInDataContainer)

    def __init__(self, name, mimetype, value):
        self.name = name
        self.mimetype = mimetype
        self.value = value

    def display_name(self):
        return self.name

    @property
    def nicknames(self):
        return [self.name, self.mimetype]
