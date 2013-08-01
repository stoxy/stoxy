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
from opennode.oms.model.form import RawDataApplier
from opennode.oms.endpoint.httprest.base import IHttpRestView
from opennode.oms.endpoint.httprest.base import HttpRestView
from opennode.oms.endpoint.httprest.base import IHttpRestSubViewFactory
from opennode.oms.endpoint.httprest.root import BadRequest
from opennode.oms.endpoint.httprest.root import NotFound
from opennode.oms.log import UserLogger
from opennode.oms.model.traversal import parse_path
from opennode.oms.util import JsonSetEncoder
from opennode.oms.zodb import db

from stoxy.server.model.container import IStorageContainer
from stoxy.server.model.container import IRootContainer
from stoxy.server.model.container import StorageContainer
from stoxy.server.model.dataobject import DataObject
from stoxy.server.model.dataobject import IDataObject


log = logging.getLogger(__name__)


class CdmiView(HttpRestView):
    context(object)

    object_constructor = StorageContainer
    object_type = 'application/cdmi-container'

    def render_object(self, obj):
        return json.dumps(self.object_to_dict(obj), cls=JsonSetEncoder)

    def object_to_dict(self, obj):
        parent_oid = (obj.__parent__.oid
                      if not IRootContainer.providedBy(obj) else None)
        return {'objectType': self.object_type,
                'objectID': obj.oid,
                'objectName': obj.name,
                'parentURI': obj.__parent__.__name__,
                'parentID': parent_oid,
                'completionStatus': 'Complete',
                'metadata': {},
                'childrenrange': '0-%d' % len(obj.listcontent()),
                'children': [child.name if IDataObject.providedBy(child)
                             else child.__name__
                             for child in obj.listcontent()]}

    def get_principal(self, request):
        interaction = request.interaction

        if not interaction:
            auth = getUtility(IAuthentication, context=None)
            principal = auth.getPrincipal(None)
        else:
            principal = interaction.participations[0].principal

        return principal

    def render_get(self, request):
        if not request.interaction.checkPermission('view', self.context):
            raise NotFound

        log.debug('Returning %s for %s' % (self.context, request))
        return self.object_to_dict(self.context)

    def render_put(self, request):
        try:
            data = json.load(request.content)
        except ValueError:
            log.error('Request content could not be parsed as JSON:\n%s', request.content)
            raise BadRequest("Input data could not be parsed")

        if not isinstance(data, dict):
            log.error('Input data was not a dictionary:\n%s', data)
            raise BadRequest("Input data must be a dictionary")

        # Assume that the name is the last element in the path
        data[u'name'] = unicode(parse_path(request.path)[-1])

        if hasattr(request, 'unresolved_path'):
            existing_object = self.context[request.unresolved_path[-1]]
        else:
            existing_object = self.context

        log.debug('existing object under %s: %s', self.context, existing_object)

        if existing_object:
            form = RawDataApplier(data, existing_object)
            action = 'apply'
        else:
            form = RawDataValidatingFactory(data, StorageContainer)
            action = 'create'

        if form.errors:
            request.setResponseCode(BadRequest.status_code)
            return {'errors': form.error_dict()}

        result_object = getattr(form, action)()

        @db.transact
        def handle_success(r, obj, principal):
            if not existing_object:
                obj.__owner__ = principal
                self.context.add(obj)
                self.add_log_event(principal, 'Creation of %s (%s) via CDMI was successful' %
                                   (obj.name, obj.__name__))
            else:
                self.add_log_event(principal, 'Update of %s (%s) via CDMI was successful' %
                                   (obj.name, obj.__name__))

            request.write(self.render_object(obj))
            log.debug('Returning %s for %s' % (obj, request))
            request.finish()

        def handle_error(f, obj, principal):
            f.trap(Exception)
            self.add_log_event(principal, '%s of %s (%s) via CDMI failed: %s: %s' %
                               ('Creation' if not existing_object else 'Update',
                                obj.name, obj.__name__, type(f.value).__name__, f.value))

            request.setResponseCode(500)
            request.write(json.dumps({'errorMessage': str(f.value)}))
            request.finish()

        principal = self.get_principal(request)
        d = handle_success(None, result_object, principal)
        d.addErrback(handle_error, result_object, principal)

        return NOT_DONE_YET

    def render_delete(self, request):
        name = unicode(parse_path(request.path)[-1])
        existing_object = self.context[name]
        if existing_object:
            del self.context[name]
        else:
            raise NotFound

    def _responseFailed(self, e, req):
        req.finish()

    def add_log_event(self, principal, msg, *args, **kwargs):
        owner = self.context.__owner__
        ulog = UserLogger(principal=principal, subject=self.context, owner=owner)
        ulog.log(msg, *args, **kwargs)
        log.debug('%s %s', principal.id, msg, *args, **kwargs)


class DataContainerView(CdmiView):
    context(IStorageContainer)


class DataObjectView(CdmiView):
    context(IDataObject)
    object_constructor = DataObject
    object_type = 'application/cdmi-object'


class StoxyViewFactory(Adapter):
    implements(IHttpRestSubViewFactory)
    context(IStorageContainer)

    def resolve(self, path, request):
        log.debug('CDMI resolving path: %s for %s', path, request)

        if request.method.lower() == 'get' and len(path) > 0:
            return

        if len(path) > 1:
            return

        request.unresolved_path = path[-1]

        return queryAdapter(self.context, IHttpRestView)
