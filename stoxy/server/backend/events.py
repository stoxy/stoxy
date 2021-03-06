import logging

from grokcore.component import subscribe

from opennode.oms.model.model.events import IModelDeletedEvent
from zope.component import getAdapter

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
    #storemgr = getAdapter(model, store.IDataStoreFactory).create()
    # TODO: passing credentials for the deletion operation is not clear atm if it's initiated via ssh
    #storemgr.delete(None)
