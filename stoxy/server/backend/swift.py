"""
OpenStack Swift data manager implementation using python-swiftclient
"""
import logging
import StringIO

from swiftclient import client
from grokcore.component import implements, name, Adapter, context

from opennode.oms.endpoint.httprest.root import BadRequest

from stoxy.server.common import parse_uri
from stoxy.server.model.dataobject import IDataObject
from stoxy.server.model.store import IDataStore


log = logging.getLogger(__name__)


class SwiftStore(Adapter):
    implements(IDataStore)
    context(IDataObject)
    name('swift')

    def save(self, datastream, encoding, credentials):
        if credentials is None:
            raise BadRequest('Swift backend requires credentials in x-auth-token headers')

        log.debug('Saving Swift object %s' % self.context.value)
        protocol, schema, host, path = parse_uri(self.context.value)
        uri = "%s:%s%s" % (schema, host, path)
        #base_path, objname = path.split('/', 1)
        #datalen = len(datastream.read())
        #datastream.seek(0)
        client.put_object(uri, credentials, contents=datastream)
        log.debug('Swift object "%s" saved' % self.context.value)

    def load(self, credentials):
        if credentials is None:
            raise BadRequest('Swift backend requires credentials in x-auth-token headers')

        log.debug('Loading Swift object %s' % self.context.value)
        protocol, schema, host, path = parse_uri(self.context.value)
        uri = "%s:%s%s" % (schema, host, path)
        base_path, objname = path.split('/', 1)
        response, contents = client.get_object(uri, credentials, base_path, objname)
        return StringIO.StringIO(contents)

    def delete(self, credentials):
        if credentials is None:
            raise BadRequest('Swift backend requires credentials in x-auth-token headers')

        log.debug('Deleting Swift object %s' % self.context.value)
        protocol, schema, host, path = parse_uri(self.context.value)
        uri = "%s:%s%s" % (schema, host, path)
        client.delete_object(uri, credentials, path)
