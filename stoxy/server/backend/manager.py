"""
Module for data managers tasked with storage of CDMI object data
"""
import logging

from grokcore.component import implements, name, Adapter, context
from zope.component import getAdapter

from opennode.oms.config import get_config

from stoxy.server.model.dataobject import IDataObject
from stoxy.server.model.store  import IDataStore, IDataStoreFactory
from stoxy.server.common import parse_uri


log = logging.getLogger(__name__)


class FileStore(Adapter):
    implements(IDataStore)
    context(IDataObject)
    name('file')

    def save(self, data):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'file', protocol
        assert not host, host
        with open(path, 'wb') as f:
            f.write(data)

    def load(self):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'file', protocol
        assert not host, host
        with open(path, 'r') as f:
            return f.read()


class Blackhole(Adapter):
    implements(IDataStore)
    context(IDataObject)
    name('null')

    def save(self, data):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'null', protocol
        assert not host, host

    def load(self):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'null', protocol
        assert not host, host


class DataStoreFactory(Adapter):
    implements(IDataStoreFactory)
    context(IDataObject)

    def make_uri(self, object_):
        path = '%s/%s' % (get_config().getstring('store', 'file_base_path', '/storage'), object_.name)
        return ('file://%s' % path, 'file', None, path)

    def create(self):
        if self.context.value:
            protocol, host, path = parse_uri(self.context.value)
        else:
            uri, protocol, host, path = self.make_uri(self.context)
            self.context.value = uri

        return getAdapter(self.context, IDataStore, protocol)
