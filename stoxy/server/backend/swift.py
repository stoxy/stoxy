"""
OpenStack Swift data manager implementation using python-swiftclient
"""
import base64
import logging
import os

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

    def save(self, datastream, encoding):
        protocol, host, path = parse_uri(self.context.value)

    def load(self):
        protocol, host, path = parse_uri(self.context.value)

    def delete(self):
        protocol, host, path = parse_uri(self.context.value)
