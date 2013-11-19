"""
Module for data managers tasked with storage of CDMI object data
"""
import logging
import os

from grokcore.component import implements, name, Adapter, context
from zope.component import getAdapter

from opennode.oms.config import get_config

from stoxy.server.model.dataobject import IDataObject
from stoxy.server.model.store import IDataStore, IDataStoreFactory
from stoxy.server.common import parse_uri


log = logging.getLogger(__name__)


class FileStore(Adapter):
    implements(IDataStore)
    context(IDataObject)
    name('file')

    def save(self, datastream):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'file', protocol
        assert not host, host
        b = 4096
        log.debug('Writing file: "%s"' % path)
        with open(path, 'wb') as f:
            d = datastream.read(b)
            f.write(d)
            while len(d) == b and not datastream.closed:
                d = datastream.read(b)
                f.write(d)

    def load(self):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'file', protocol
        assert not host, host
        return open(path, 'rb')

    def delete(self):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'file', protocol
        assert not host, host
        log.debug('Unlinking "%s"' % path)
        os.unlink(path)


class Blackhole(Adapter):
    implements(IDataStore)
    context(IDataObject)
    name('null')

    def save(self, datastream):
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
