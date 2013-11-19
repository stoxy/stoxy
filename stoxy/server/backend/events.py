import logging

from grokcore.component import subscribe
from twisted.internet import defer
from twisted.internet import task
from twisted.internet import reactor
from zope.authentication.interfaces import IAuthentication
from zope.component import getUtility
from zope.component import getAdapter

from opennode.oms.config import get_config
from opennode.oms.model.model.events import IModelDeletedEvent
from opennode.oms.model.traversal import canonical_path, traverse1
from opennode.oms.security.authentication import sudo
from opennode.oms.zodb import db

from stoxy.server.model import container
from stoxy.server.model import dataobject
from stoxy.server.model import store


log = logging.getLogger(__name__)


@subscribe(container.StorageContainer, IModelDeletedEvent)
def handle_container_delete(model, event):
    log.debug('Deleting container: "%s"' % model)


@subscribe(dataobject.DataObject, IModelDeletedEvent)
def handle_dataobject_delete(model, event):
    log.debug('Deleting object: "%s"' % model)
    storemgr = getAdapter(model, store.IDataStoreFactory).create()
    storemgr.delete()
