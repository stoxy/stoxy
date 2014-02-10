"""
Module for data managers tasked with storage of CDMI object data
"""
import base64
import logging
import os
import StringIO

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

    def save(self, datastream, encoding, credentials=None):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'file', protocol
        assert not host, host
        b = 6 * 1024
        log.debug('Writing file: "%s"' % path)
        with open(path, 'wb') as f:
            d = datastream.read(b)
            if encoding == 'base64':
                d = base64.b64decode(d)
            f.write(d)
            while len(d) == b and not datastream.closed:
                d = datastream.read(b)
                f.write(d)

    def load(self, credentials=None):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'file', protocol
        assert not host, host
        return open(path, 'rb')

    def delete(self, credentials=None):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'file', protocol
        assert not host, host
        log.debug('Unlinking "%s"' % path)
        os.unlink(path)


class Blackhole(Adapter):
    implements(IDataStore)
    context(IDataObject)
    name('null')

    def save(self, datastream, encoding, credentials=None):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'null', protocol
        assert not host, host

    def load(self, credentials=None):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'null', protocol
        assert not host, host

        return StringIO.StringIO('')

    def delete(self, credentials=None):
        protocol, host, path = parse_uri(self.context.value)
        assert protocol == 'null', protocol
        assert not host, host


class DataStoreFactory(Adapter):
    implements(IDataStoreFactory)
    context(IDataObject)

    def make_uri(self, object_):
        # get backend of the parent container
        parent_md = object_.__parent__.metadata
        backend = parent_md.get('stoxy_backend', 'file')
        backend_base = parent_md.get('stoxy_backend_base',
                                     get_config().getstring('store', 'file_base_path', '/tmp'))
        path = '%s/%s' % (backend_base, object_.name)
        uri = '%s://%s' % (backend, path)
        log.debug('Constructed internal uri %s' % uri)
        return (uri, backend, None, path)

    def create(self):
        if self.context.value:
            protocol, host, path = parse_uri(self.context.value)
        else:
            # XXX we actually discard all but the host part
            uri, protocol, host, path = self.make_uri(self.context)
            self.context.value = uri

        return getAdapter(self.context, IDataStore, protocol)
