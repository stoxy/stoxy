import json
import logging

from grokcore.component import Adapter
from grokcore.component import implements
from grokcore.component import context
from twisted.web.server import NOT_DONE_YET
from zope.authentication.interfaces import IAuthentication
from zope.component import getUtility
from zope.component import queryAdapter

from opennode.oms.model.form import RawDataValidatingFactory
from opennode.oms.endpoint.httprest.base import IHttpRestView
from opennode.oms.endpoint.httprest.base import IHttpRestSubViewFactory
from opennode.oms.endpoint.httprest.root import BadRequest
from opennode.oms.endpoint.httprest.view import ContainerView
from opennode.oms.endpoint.httprest.view import DefaultView
from opennode.oms.log import UserLogger
from opennode.oms.model.traversal import parse_path
from opennode.oms.util import JsonSetEncoder
from opennode.oms.zodb import db

from stoxy.server.model.container import IStorageContainer
from stoxy.server.model.container import StorageContainer
from stoxy.server.model.dataobject import DataObject
from stoxy.server.model.dataobject import IDataObject


log = logging.getLogger(__name__)


class DataContainerView(ContainerView):
    context(IStorageContainer)

    def render_object(self, container):
        return json.dumps({
            'objectType': 'application/cdmi-container',
            'objectID': container.__name__,
            'objectName': container.name,
            'parentURI': container.__parent__.__name__,
            'parentID': container.__parent__.__name__,
            'completionStatus': 'Complete',
            'metadata': {},
            'childrenrange': '0-%d' % len(container.listcontent()),
            'children': [child.name if IDataObject.providedBy(child)
                         else child.__name__
                         for child in container.listcontent()]
        }, cls=JsonSetEncoder)

    def get_principal(self, request):
        interaction = request.interaction

        if not interaction:
            auth = getUtility(IAuthentication, context=None)
            principal = auth.getPrincipal(None)
        else:
            principal = interaction.participations[0].principal

        return principal

    def render_put(self, request):
        try:
            data = json.load(request.content)
        except ValueError:
            log.error('Request content could not be parsed as JSON:\n%s', request.content)
            raise BadRequest("Input data could not be parsed")

        if not isinstance(data, dict):
            log.error('Input data was not a dictionary:\n%s', data)
            raise BadRequest("Input data must be a dictionary")

        log.debug('Received data: %s', data)
        if 'metadata' in data or u'metadata' in data:
            del data['metadata']

        # Assume that the name is the last element in the path
        data['name'] = parse_path(request.path)[-1]

        form = RawDataValidatingFactory(data, StorageContainer)

        if form.errors:
            log.error(data)
            request.setResponseCode(BadRequest.status_code)
            return form.error_dict()

        principal = self.get_principal(request)

        container = form.create()

        @db.transact
        def handle_success(r, container, principal):
            container.__owner__ = principal
            self.context.add(container)
            data['id'] = container.__name__

            self.add_log_event(principal, 'Creation of %s (%s) via CDMI was successful' %
                               (container.name, container.__name__))

            request.write(self.render_object(container))
            request.finish()

        def handle_error(f, container, principal):
            f.trap(Exception)
            self.add_log_event(principal, 'Creation of %s (%s) (via web) failed: %s: %s' %
                               (container.name, container.__name__, type(f.value).__name__, f.value))

            request.setResponseCode(500)
            request.write(json.dumps({'errorMessage': str(f.value)}))
            request.finish()

        d = handle_success(None, container, principal)
        d.addErrback(handle_error, container, principal)

        return NOT_DONE_YET

    def _responseFailed(self, e, req):
        req.finish()

    def add_log_event(self, principal, msg, *args, **kwargs):
        owner = self.context.__owner__
        ulog = UserLogger(principal=principal, subject=self.context, owner=owner)
        ulog.log(msg, *args, **kwargs)
        log.debug('%s %s', principal.id, msg, *args, **kwargs)


class StoxyViewFactory(Adapter):
    implements(IHttpRestSubViewFactory)
    context(IStorageContainer)

    def resolve(self, path, method):
        log.debug('CDMI resolving path: %s for a %s request', path, method)

        if method.lower() == 'get' and len(path) > 0:
            return

        if len(path) > 1:
            return

        return queryAdapter(self.context, IHttpRestView)


class DataObjectView(DefaultView):
    context(IDataObject)

    def render_object(self, o):
        return json.dumps({
            'objectType': 'application/cdmi-object',
            'objectID': o.__name__,
            'objectName': o.name,
            'parentURI': o.__parent__.__name__,
            'parentID': o.__parent__.__name__,
            'completionStatus': 'Complete',
            'metadata': {},
        }, cls=JsonSetEncoder)

    def render_put(self, request):
        try:
            data = json.load(request.content)
        except ValueError:
            raise BadRequest("Input data could not be parsed")

        if not isinstance(data, dict):
            raise BadRequest("Input data must be a dictionary")

        if 'metadata' in data:
            del data['metadata']

        form = RawDataValidatingFactory(data, DataObject)

        if not form.errors:
            form.create()
            return [IHttpRestView(self.context).render_recursive(request, depth=0)]
        else:
            request.setResponseCode(BadRequest.status_code)
            return form.error_dict()
