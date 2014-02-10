"""
OpenStack Swift data manager implementation using python-swiftclient
"""
import base64
import logging
import os
import StringIO

from grokcore.component import implements, name, Adapter, context

from opennode.oms.config import get_config

from stoxy.server.model.dataobject import IDataObject
from stoxy.server.model.store import IDataStore
from stoxy.server.common import parse_uri


log = logging.getLogger(__name__)


class SwiftStore(Adapter):
    implements(IDataStore)
    context(IDataObject)
    name('swift')

    def save(self, datastream, encoding, credentials):
        log.debug('Saving Swift object %s' % self.context.value)
        protocol, host, path = parse_uri(self.context.value)

    def load(self, credentials):
        log.debug('Loading Swift object %s' % self.context.value)
        protocol, host, path = parse_uri(self.context.value)
        return StringIO.StringIO()

    def delete(self, credentials):
        log.debug('Deleting Swift object %s' % self.context.value)
        protocol, host, path = parse_uri(self.context.value)
