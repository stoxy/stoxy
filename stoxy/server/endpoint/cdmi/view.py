import base64
import json
import logging
import functools
import io
import StringIO

from grokcore.component import Adapter
from grokcore.component import implements
from grokcore.component import context
from twisted.web.server import NOT_DONE_YET
from twisted.internet import defer
from twisted.internet.interfaces import IPullProducer
from zope.authentication.interfaces import IAuthentication
from zope.component import getUtility
from zope.component import getAdapter
from zope.component import handle
from zope.component import queryAdapter

from opennode.oms.endpoint.httprest.base import IHttpRestView
from opennode.oms.endpoint.httprest.base import HttpRestView
from opennode.oms.endpoint.httprest.base import IHttpRestSubViewFactory
from opennode.oms.endpoint.httprest.root import BadRequest
from opennode.oms.endpoint.httprest.root import NotFound
from opennode.oms.log import UserLogger
from opennode.oms.model.model.events import ModelDeletedEvent
from opennode.oms.model.traversal import parse_path
from opennode.oms.util import JsonSetEncoder
from opennode.oms.zodb import db

from stoxy.server.model.container import IStorageContainer
from stoxy.server.model.container import IInStorageContainer
from stoxy.server.model.container import IRootContainer
from stoxy.server.model.container import RootStorageContainer
from stoxy.server.model.container import StorageContainer
from stoxy.server.model.dataobject import DataObject
from stoxy.server.model.capability import ISystemCapability
from stoxy.server.model.capability import SystemCapability
from stoxy.server.model.dataobject import IDataObject

from stoxy.server.model.store import IDataStoreFactory
from stoxy.server.model.form import CdmiObjectValidatorFactory
from stoxy.server import common
from stoxy.server.endpoint.cdmi import current_capabilities


log = logging.getLogger(__name__)


def response_headers(f):
    @functools.wraps(f)
    def _wrapper_for_render_method(self, request, *args, **kw):
        self.set_response_headers(request)
        return f(self, request, *args, **kw)
    return _wrapper_for_render_method


class DataStreamProducer(object):
    implements(IPullProducer)
    MAX_CHUNK = 2 ** 16
    def beginSendingData(self, datastream, consumer, begin=0, end=None):
        self.consumer = consumer
        self.datastream = datastream
        self.begin = begin
        self.end = end
        self.deferred = deferred = defer.Deferred()
        self.lastSent = ''
        self.consumer.registerProducer(self, False)
        return deferred

    def resumeProducing(self):
        if self.datastream.tell() >= self.end:
            log.debug('Finished writing data! %s->%s:%s' % (self.datastream.tell(), self.begin, self.end))
            self.datastream = None
            self.consumer.unregisterProducer()
            if self.deferred:
                self.deferred.callback(self.lastSent)
                self.deferred = None
            self.consumer.finish()
            return

        if self.datastream.tell() < self.begin:
            self.datastream.seek(self.begin)

        data = self.datastream.read(min(self.MAX_CHUNK, max(0, self.end - self.datastream.tell()
                                                            if self.end else self.MAX_CHUNK)))
        self.consumer.write(data)
        self.lastSent = data[-1:]

    def stopProducing(self):
        self.datastream.close()


class CdmiView(HttpRestView):

    context(IInStorageContainer)

    object_constructor_map = {'application/cdmi-container': StorageContainer,
                              'application/cdmi-object': DataObject}

    object_type_map = {StorageContainer: 'application/cdmi-container',
                       RootStorageContainer: 'application/cdmi-container',
                       DataObject: 'application/cdmi-object',
                       SystemCapability: 'application/cdmi-capability'}

    @classmethod
    def set_response_headers(cls, request):
        request.setHeader('X-CDMI-Specification-Version', common.CDMI_VERSION)

    def render_object(self, obj):
        return json.dumps(self.object_to_dict(obj), cls=JsonSetEncoder)

    def get_additional_data(self, obj, attrs=None):
        return {}

    def object_to_dict(self, obj, attrs=None):

        def filter_attr(attr, attrs):
            return not attrs or attr in attrs.keys()

        def get_data(obj, begin=0, end=None):
            datastream = self.load_object(obj)

            if datastream.tell() < begin:
                datastream.seek(begin)

            if isinstance(end, int):
                data = datastream.read(end - begin)
            else:
                data = datastream.read()

            return base64.b64encode(data)

        def object_data_generator(obj, attrs=dict()):
            yield ('objectType', lambda: self.object_type_map[obj.type])
            yield ('objectID', lambda: obj.oid)
            yield ('objectName', lambda: obj.name)
            yield ('parentURI', lambda: obj.__parent__.__name__)
            yield ('parentID', lambda: (obj.__parent__.oid
                                        if (not IRootContainer.providedBy(obj)
                                            and not ISystemCapability.providedBy(obj))
                                        else None))
            yield ('completionStatus', lambda: 'Complete')  # TODO: report errors / incomplete status
            isComplete = True

            if IStorageContainer.providedBy(obj) or IDataObject.providedBy(obj):
                yield ('metadata', lambda: dict(obj.metadata))

            if IStorageContainer.providedBy(obj):
                yield ('children', lambda: [(child.name if IDataObject.providedBy(child)
                                             else child.__name__) for child in obj.listcontent()])
                yield ('childrenrange', lambda: '0-%d' % len(obj.listcontent()))
            elif IDataObject.providedBy(obj) and isComplete:
                if attrs and 'value' in attrs:
                    begin, end = attrs['value']
                else:
                    begin = 0
                    end = None
                yield ('value', lambda: get_data(obj, begin=begin, end=end))
                yield ('valuetransferencoding', lambda: 'base64')
            elif ISystemCapability.providedBy(obj):
                yield ('children', lambda: [])
                yield ('childrenrange', lambda: '0-0'),
                yield ('capabilities', lambda: current_capabilities.system)

        # filter for requested attributes
        filtered_generator = [(k, vg) for k, vg in object_data_generator(obj, attrs=attrs)
                              if filter_attr(k, attrs)]

        # evaluate generators and construct the final dict
        data = dict([(k, vg()) for k, vg  in filtered_generator])
        data.update(self.get_additional_data(obj, attrs=attrs))
        return data

    def get_principal(self, request):
        interaction = request.interaction

        if not interaction:
            auth = getUtility(IAuthentication, context=None)
            return auth.getPrincipal(None)
        else:
            return interaction.participations[0].principal

    @response_headers
    def render_get(self, request):
        if not request.interaction.checkPermission('view', self.context):
            raise NotFound

        cdmi = request.getHeader('X-CDMI-Specification-Version')

        if cdmi or not IDataObject.providedBy(self.context):
            request.setHeader('Content-Type', self.object_type_map[self.context.type])
            log.debug('Received arguments: %s', request.args)
            attrs = dict(self.parse_args_to_filter_attrs(request.args))
            return self.object_to_dict(self.context, attrs=attrs)
        else:
            return self.handle_noncdmi_get(request)

    def parse_args_to_filter_attrs(self, args):
        for key, val in args.iteritems():
            if key == 'value':
                values = map(int, val)
                begin = min(values)
                end = max(values)
                yield ('value', [begin, end])
            elif key == 'metadata':
                yield ('metadata', val)
            else:
                yield (key, None)

    def handle_noncdmi_get(self, request):
        log.debug('Processing request as non-CDMI')
        request.setHeader('Content-Type', self.context.mimetype.encode('ascii'))
        byterange = request.getHeader('Range')

        begin = 0
        end = None

        if byterange is not None:
            begin, end = map(int, byterange.split('-'))
            log.debug('Getting range %d:%d' % (begin, end))

        datastream = self.load_object(self.context)
        d = DataStreamProducer().beginSendingData(datastream, request, begin, end)
        d.addBoth(lambda r: log.debug('Finished sending data'))

        return NOT_DONE_YET

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

    def store_object(self, obj, datastream, encoding):
        storemgr = getAdapter(obj, IDataStoreFactory).create()
        storemgr.save(datastream, encoding)

    def load_object(self, obj):
        storemgr = getAdapter(obj, IDataStoreFactory).create()
        return storemgr.load()

    @db.transact
    def handle_success(self, r, request, obj, principal, update, dstream, encoding):
        if not update:
            obj.__owner__ = principal
            self.context.add(obj)

        if IDataObject.providedBy(obj):
            self.store_object(obj, dstream, encoding)

        self.add_log_event(principal, '%s of %s (%s) via CDMI was successful' %
                           ('Creation' if not update else 'Update', obj.name, obj.__name__))

    def handle_error(self, f, request, obj, principal, update):
        f.trap(Exception)
        if request.finished:  # Should not be triggered at all
            try:
                f.raiseException()
            except Exception:
                log.error('Connection lost: cannot return error message to the client. %s', request,
                          exc_info=True)
            return

        self.add_log_event(principal, '%s of %s (%s) via CDMI failed: %s: %s' %
                           ('Creation' if not update else 'Update',
                            obj.name, obj.__name__, type(f.value).__name__, f.value))

        try:
            f.raiseException()
        except defer.CancelledError:
            return
        except Exception:
            log.debug('Error debugging info', exc_info=True)

        request.setResponseCode(500)
        request.write(json.dumps({'errorMessage': str(f.value)}))
        request.finish()

    def finish_response(self, r, request, obj, noncdmi=False):
        if request.finished:  # Should not be triggered at all
            log.error('Connection lost: cannot render resulting object. '
                      'Modifications were saved. %s', request)
            return

        if not noncdmi:
            request.write(self.render_object(obj))

        request.finish()

    @response_headers
    def render_put(self, request):
        existing_object = self.context if not hasattr(request, 'unresolved_path') else None

        requested_type = request.getHeader('content-type')
        content_length = request.getHeader('content-length')

        if requested_type is None:
            log.error('content-type not found in %s', request.getAllHeaders())
            raise BadRequest('No Content-Type specified')

        data = {}
        noncdmi = False

        if requested_type not in self.object_constructor_map.keys():
            noncdmi = True
            data[u'mimetype'] = requested_type
            requested_type = 'application/cdmi-object'
            dstream = request.content
            data[u'value'] = None
            data[u'content_length'] = content_length
        elif requested_type == 'application/cdmi-object':
            data = self._parse_and_validate_data(request)
            dstream = StringIO.StringIO(data.get('value', ''))
            data[u'value'] = None
        else:
            dstream = io.BytesIO()

        if existing_object:
            data[u'name'] = unicode(parse_path(request.path)[-1])
            form = CdmiObjectValidatorFactory.get_applier(existing_object, data)
            request.setHeader('content-type', self.object_type_map[existing_object.type])
            action = 'apply'
        else:
            data[u'name'] = unicode(request.unresolved_path)
            requested_class = self.object_constructor_map[requested_type]
            form = CdmiObjectValidatorFactory.get_creator(requested_class, data)
            request.setHeader('content-type', requested_type)
            action = 'create'

        if form.errors:
            log.error('Validation failed: %s (%s):\n%s', form, request, form.errors)
            request.setResponseCode(BadRequest.status_code)
            return form.error_dict()

        result_object = getattr(form, action)()

        principal = self.get_principal(request)
        d = self.handle_success(None, request, result_object, principal, existing_object, dstream,
                                data.get(u'valuetransferencoding', 'utf-8'))
        connection_lost = request.notifyFinish()
        connection_lost.addBoth(lambda r: d.cancel())
        d.addCallback(self.finish_response, request, result_object, noncdmi)
        d.addErrback(self.handle_error, request, result_object, principal, existing_object)

        return NOT_DONE_YET

    @response_headers
    def render_delete(self, request):
        name = unicode(parse_path(request.path)[-1])
        existing_object = self.context.__parent__[name]
        if existing_object:
            log.debug('Deleting %s', self.context)
            del self.context.__parent__[name]
            handle(self.context, ModelDeletedEvent(self.context.__parent__))
        else:
            raise NotFound

    def add_log_event(self, principal, msg, *args, **kwargs):
        owner = self.context.__owner__
        ulog = UserLogger(principal=principal, subject=self.context, owner=owner)
        ulog.log(msg, *args, **kwargs)


class DataContainerView(CdmiView):
    context(IStorageContainer)
    object_constructor = StorageContainer
    object_type = 'application/cdmi-container'


class DataObjectView(CdmiView):
    context(IDataObject)
    object_constructor = DataObject
    object_type = 'application/cdmi-object'


class CapabilityView(CdmiView):
    context(ISystemCapability)
    object_constructor = SystemCapability
    object_type = 'application/cdmi-capability'


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
