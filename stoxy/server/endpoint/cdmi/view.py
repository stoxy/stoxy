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
from stoxy.server.model.container import RootStorageContainer
from stoxy.server.model.container import StorageContainer
from stoxy.server.model.dataobject import DataObject
from stoxy.server.model.dataobject import IDataObject
from stoxy.server.model.form import CdmiObjectValidatorFactory
from stoxy.server import common


log = logging.getLogger(__name__)


def response_headers(f):
    @functools.wraps(f)
    def _wrapper_for_render_method(self, request, *args, **kw):
        self.set_response_headers(request)
        return f(self, request, *args, **kw)
    return _wrapper_for_render_method


class CdmiView(HttpRestView):
    context(object)

    object_constructor_map = {'application/cdmi-container': StorageContainer,
                              'application/cdmi-object': DataObject}

    object_type_map = {StorageContainer: 'application/cdmi-container',
                       RootStorageContainer: 'application/cdmi-container',
                       DataObject: 'application/cdmi-object'}

    @classmethod
    def set_response_headers(cls, request):
        request.setHeader('X-CDMI-Specification-Version', common.CDMI_VERSION)

    def render_object(self, obj):
        return json.dumps(self.object_to_dict(obj), cls=JsonSetEncoder)

    def get_additional_data(self, obj):
        return {}

    def object_to_dict(self, obj):
        parent_oid = (obj.__parent__.oid if not IRootContainer.providedBy(obj) else None)

        data = {'objectType': self.object_type_map[obj.type],
                'objectID': obj.oid,
                'objectName': obj.name,
                'parentURI': obj.__parent__.__name__,
                'parentID': parent_oid,
                'completionStatus': 'Complete',
                'metadata': dict(obj.metadata),
                'childrenrange': '0-%d' % len(obj.listcontent()),
                'children': [child.name if IDataObject.providedBy(child)
                             else child.__name__
                             for child in obj.listcontent()]}

        data.update(self.get_additional_data(obj))
        return data

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

    def _parse_and_validate_data(self, request):
        try:
            data = json.load(request.content)
        except ValueError:
            log.error('Request content could not be parsed as JSON:\n%s', request.content)
            raise BadRequest("Input data could not be parsed")

        if not isinstance(data, dict):
            log.error('Input data was not a dictionary:\n%s', data)
            raise BadRequest("Input data must be a dictionary")

        return data

    @response_headers
    def render_put(self, request):
        data = self._parse_and_validate_data(request)

        existing_object = self.context if not hasattr(request, 'unresolved_path') else None

        requested_type = request.getHeader('content-type')

        if requested_type is None:
            log.error('content-type not found in %s', request.getAllHeaders())
            raise BadRequest('No Content-Type specified')

        if requested_type not in self.object_constructor_map.keys():
            raise BadRequest('Don\'t know how to create objects of type: %s' % requested_type)

        if existing_object:
            data[u'name'] = unicode(parse_path(request.path)[-1])
            form = CdmiObjectValidatorFactory.get_applier(existing_object, data)
            request.setHeader('content-type', self.object_type_map[existing_object.type])
            action = 'apply'
        else:
            requested_class = self.object_constructor_map[requested_type]
            data[u'name'] = unicode(request.unresolved_path[-1])
            request.setHeader('content-type', requested_type)
            form = CdmiObjectValidatorFactory.get_creator(requested_class, data)
            action = 'create'

        if form.errors:
            log.error('Validation failed: %s (%s):\n%s', form, request, form.errors)
            request.setResponseCode(BadRequest.status_code)
            return form.error_dict()

        result_object = getattr(form, action)()

        @db.transact
        def handle_success(r, request, obj, principal):
            if not existing_object:
                obj.__owner__ = principal
                self.context.add(obj)

            self.add_log_event(principal, '%s of %s (%s) via CDMI was successful' %
                               ('Creation' if not existing_object else 'Update', obj.name, obj.__name__))

        def finish_response(r, request, obj):
            if request.finished:  # Should not be triggered at all
                log.error('Connection lost: cannot render resulting object. '
                          'Modifications were saved. %s', request)
                return
            request.write(self.render_object(obj))
            request.finish()

        def handle_error(f, request, obj, principal):
            f.trap(Exception)
            if request.finished:  # Should not be triggered at all
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
    object_constructor = StorageContainer
    object_type = 'application/cdmi-container'


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
