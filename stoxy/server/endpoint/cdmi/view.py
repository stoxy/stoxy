import json
import logging
import functools

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
from stoxy.server import common


log = logging.getLogger(__name__)


def response_headers(f):
    @functools.wraps(f)
    def _wrapper_for_render_method(self, request, *args, **kw):
        CdmiView.set_response_headers(request)
        return f(self, request, *args, **kw)
    return _wrapper_for_render_method


class CdmiView(HttpRestView):
    context(object)

    object_constructor = StorageContainer
    object_type = 'application/cdmi-container'

    @classmethod
    def set_response_headers(cls, request):
        request.setHeader('Content-Type', cls.object_type)
        request.setHeader('X-CDMI-Specification-Version', common.CDMI_VERSION)

    def render_object(self, obj):
        return json.dumps(self.object_to_dict(obj), cls=JsonSetEncoder)

    def object_to_dict(self, obj):
        parent_oid = (obj.__parent__.oid if not IRootContainer.providedBy(obj) else None)

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

    @response_headers
    def render_get(self, request):
        if not request.interaction.checkPermission('view', self.context):
            raise NotFound

        return self.object_to_dict(self.context)

    @response_headers
    def render_put(self, request):
        try:
            data = json.load(request.content)
        except ValueError:
            log.error('Request content could not be parsed as JSON:\n%s', request.content)
            raise BadRequest("Input data could not be parsed")

        if not isinstance(data, dict):
            log.error('Input data was not a dictionary:\n%s', data)
            raise BadRequest("Input data must be a dictionary")

        existing_object = self.context if not hasattr(request, 'unresolved_path') else None

        if existing_object:
            form = RawDataApplier(data, existing_object)
            action = 'apply'
        else:
            data[u'name'] = unicode(request.unresolved_path[-1])
            form = RawDataValidatingFactory(data, self.object_constructor)
            action = 'create'

        if form.errors:
            request.setResponseCode(BadRequest.status_code)
            return {'errors': form.error_dict()}

        result_object = getattr(form, action)()

        @db.transact
        def handle_success(r, request, obj, principal):
            if not existing_object:
                obj.__owner__ = principal
                self.context.add(obj)
                self.add_log_event(principal, 'Creation of %s (%s) via CDMI was successful' %
                                   (obj.name, obj.__name__))
            else:
                self.add_log_event(principal, 'Update of %s (%s) via CDMI was successful' %
                                   (obj.name, obj.__name__))

        def finish_response(r, request, obj):
            if request.finished:
                log.error('Connection lost: cannot render resulting object. Modifications were saved. %s',
                          request)
                return
            request.write(self.render_object(obj))
            request.finish()

        def handle_error(f, request, obj, principal):
            f.trap(Exception)
            if request.finished:
                try:
                    f.raiseException()
                except Exception:
                    log.error('Connection lost: cannot return error message to the client. %s', request,
                              exc_info=True)
                return

            self.add_log_event(principal, '%s of %s (%s) via CDMI failed: %s: %s' %
                               ('Creation' if not existing_object else 'Update',
                                obj.name, obj.__name__, type(f.value).__name__, f.value))

            request.setResponseCode(500)
            request.write(json.dumps({'errorMessage': str(f.value)}))
            request.finish()

        principal = self.get_principal(request)
        d = handle_success(None, request, result_object, principal)
        connection_lost = request.notifyFinish()
        connection_lost.addCallback(lambda r: d.cancel())
        d.addCallback(finish_response, request, result_object)
        d.addErrback(handle_error, request, result_object, principal)

        return NOT_DONE_YET

    @response_headers
    def render_delete(self, request):
        name = unicode(parse_path(request.path)[-1])
        existing_object = self.context[name]
        if existing_object:
            del self.context[name]
        else:
            raise NotFound

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
        if request.method.lower() == 'get' and len(path) > 0:
            return

        if len(path) > 1:
            return

        request.unresolved_path = path[-1]

        return queryAdapter(self.context, IHttpRestView)
