from __future__ import absolute_import

from grokcore.component import implements
from zope import schema
from zope.interface import Interface

from opennode.oms.model.model.base import IDisplayName
from opennode.oms.model.model.base import Model

from stoxy.server import common
from stoxy.server.model.container import IInStorageContainer


class IDataObject(Interface):
    oid = schema.TextLine(title=u"CDMI Object ID",
                          max_length=common.OBJECTID_MAX_BYTES * common.BASE16_SIZE_MULTIPLIER,
                          min_length=common.OBJECTID_MIN_BYTES * common.BASE16_SIZE_MULTIPLIER,
                          required=False)
    name = schema.TextLine(title=u"Data object name", required=True)
    mimetype = schema.TextLine(title=u"MIME type of the data", required=True)
    value = schema.TextLine(title=u"Value URI", required=False, default=None)
    metadata = schema.Dict(title=u'Metadata', key_type=schema.TextLine(), value_type=schema.TextLine(),
                           required=False)
    content_length = schema.Int(title=u"Content length", description=u"Content length of the object",
                                required=False)


class DataObject(Model):
    implements(IDataObject, IDisplayName, IInStorageContainer)

    def __init__(self, oid=None, name=None, mimetype=None, value=None, metadata={}, content_length=None):
        self.oid = unicode(common.generate_guid_b16() if oid is None else oid)
        self.__name__ = name
        self.mimetype = mimetype
        self.value = value
        self.metadata = metadata
        self.content_length = content_length

    @property
    def name(self):
        return self.__name__

    def display_name(self):
        return self.name

    @property
    def nicknames(self):
        return [self.name, self.mimetype]

    def __str__(self):
        return '<DataObject ObjectID=%s name=%s>' % (self.oid, self.name)

    @property
    def type(self):
        return DataObject
