import base64
import functools
import json
import logging
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
from opennode.oms.model.model.byname import ByNameContainer
from opennode.oms.model.model.actions import ActionsContainer
from opennode.oms.model.traversal import parse_path
from opennode.oms.util import JsonSetEncoder
from opennode.oms.zodb import db

from stoxy.server import common
from stoxy.server.endpoint.cdmi import current_capabilities
from stoxy.server.model.capability import ISystemCapability
from stoxy.server.model.capability import SystemCapability
from stoxy.server.model.container import IStorageContainer
from stoxy.server.model.container import IInStorageContainer
from stoxy.server.model.container import IRootContainer
from stoxy.server.model.container import RootStorageContainer
from stoxy.server.model.container import StorageContainer
from stoxy.server.model.container import ObjectIdContainer
from stoxy.server.model.dataobject import DataObject
from stoxy.server.model.dataobject import IDataObject
from stoxy.server.model.form import CdmiObjectValidatorFactory
from stoxy.server.model.store import IDataStoreFactory


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

        data = self.datastream.read(min(self.MAX_CHUNK,
                                        max(0, self.end - self.datastream.tell()
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

    def render_object(self, obj, request, render_value):
        """Render an object into JSON. If render_value is True, render load and render also the content"""
        return json.dumps(self.object_to_dict(obj, request, render_value=render_value), cls=JsonSetEncoder)

    def get_additional_data(self, obj, attrs=None):
        return {}

    def object_to_dict(self, obj, request, attrs={}, render_value=True):

        def filter_attr(attr, attrs):
            return attrs is None or len(attrs) == 0 or attr in attrs.keys()

        def get_data(obj, begin=0, end=None):
            datastream = self.load_object(obj, request.getHeader('X-Auth-Token'))

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

            if IStorageContainer.providedBy(obj) or IDataObject.providedBy(obj):
                yield ('metadata', lambda: dict(obj.metadata))

            if isinstance(obj, ObjectIdContainer):
                yield ('children', lambda: [(child.oid if IInStorageContainer.providedBy(child)
                                             else child.__name__) for child in obj.listcontent()])
                yield ('childrenrange', lambda: '0-%d' % len(obj.listcontent()))
            elif IStorageContainer.providedBy(obj):
                yield ('children', lambda: [(child.name if IDataObject.providedBy(child)
                                             else child.__name__) for child in obj.listcontent()])
                yield ('childrenrange', lambda: '0-%d' % len(obj.listcontent()))
            elif IDataObject.providedBy(obj) and render_value:
                # NOTE: 'value' attribute name is mandated by the specification
                if 'value' in attrs:
                    begin, end = (int(v) for v in attrs['value'])
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
        log.debug('Requested attributes: %s; attrs: %s' % ([k for k, v in filtered_generator], attrs))
        # evaluate generators and construct the final dict
        data = dict([(k, vg()) for k, vg in filtered_generator])
        data.update(self.get_additional_data(obj, attrs=attrs))
        return data

    def get_principal(self, request):
        interaction = request.interaction

        if not interaction:
            auth = getUtility(IAuthentication, context=None)
            return auth.getPrincipal(None)
        else:
            return interaction.participations[0].principal

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

        # XXX: It should not be the only option to get authentication credentials
        datastream = self.load_object(self.context, request.getHeader('X-Auth-Token'))
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

    def store_object(self, obj, datastream, encoding, credentials, **kwargs):
        storemgr = getAdapter(obj, IDataStoreFactory).create()
        storemgr.save(datastream, encoding, credentials, **kwargs)

    def load_object(self, obj, credentials, **kwargs):
        storemgr = getAdapter(obj, IDataStoreFactory).create()
        return storemgr.load(credentials, **kwargs)

    @db.transact
    def handle_success(self, r, request, obj, principal, update, dstream, encoding):
        if not update:
            obj.__owner__ = principal
            self.context.add(obj)

        if IDataObject.providedBy(obj):
            # XXX this is a hack and it doesn't feel the extraction should
            # happen here. But cannot come up with smarter ideas at the moment
            credentials = request.getHeader('X-Auth-Token')
            self.store_object(obj, dstream, encoding, credentials)

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

        log.error('%s of %s (%s) via CDMI failed: %s: %s' %
                  ('Creation' if not update else 'Update',
                   obj.name, obj.__name__, type(f.value).__name__, f.value))

        try:
            f.raiseException()
        except defer.CancelledError:
            return
        except BadRequest:
            request.setResponseCode(400)
        except Exception:
            log.debug('Error debugging info', exc_info=True)
            request.setResponseCode(500)

        request.write(json.dumps({'errorMessage': str(f.value)}))
        request.finish()

    def finish_response(self, r, request, obj, noncdmi=False, render_value=True):
        if request.finished:  # Should not be triggered at all
            log.error('Connection lost: cannot render resulting object. '
                      'Modifications were saved. %s', request)
            return

        if not noncdmi:
            request.write(self.render_object(obj, request, render_value=render_value))

        request.finish()

    @response_headers
    def render_get(self, request):
        if not request.interaction.checkPermission('view', self.context):
            raise NotFound

        cdmi = request.getHeader('X-CDMI-Specification-Version')

        if cdmi or not IDataObject.providedBy(self.context):
            request.setHeader('Content-Type', self.object_type_map[self.context.type])
            log.debug('Received arguments: %s', request.args)
            attrs = dict(self.parse_args_to_filter_attrs(request.args))
            return self.object_to_dict(self.context, request, attrs=attrs)
        else:
            return self.handle_noncdmi_get(request)

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
            dstream = request.content
            data[u'content_length'] = content_length
            data[u'mimetype'] = requested_type
            data[u'value'] = None
            # set to a 'correct' one - the only supported via CDMI
            requested_type = 'application/cdmi-object'
        elif requested_type == 'application/cdmi-object':
            data = self._parse_and_validate_data(request)
            dstream = StringIO.StringIO(data.get('value', ''))
            data[u'value'] = None
        elif requested_type == 'application/cdmi-container':
            dstream = io.BytesIO()
            data = self._parse_and_validate_data(request)
        else:
            raise BadRequest('Cannot handle PUT for the request object type %s' % requested_type)

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
        d.addCallback(self.finish_response, request, result_object, noncdmi, render_value=False)
        d.addErrback(self.handle_error, request, result_object, principal, existing_object)

        return NOT_DONE_YET

    @response_headers
    def render_delete(self, request):
        name = unicode(parse_path(request.path)[-1])
        existing_object = self.context.__parent__[name]
        if existing_object:
            log.debug('Deleting %s', self.context)
            # are we deleting a container?
            if IStorageContainer.providedBy(self.context):
                # check children
                children = [child for child in self.context.listcontent() if
                                       IDataObject.providedBy(child) or
                                       IStorageContainer.providedBy(child)]
                if len(children) > 0:
                    raise BadRequest('Attempt to delete a non-empty container')
            else:
                # XXX: Alternative authentication methods!
                credentials = request.getHeader('X-Auth-Token')
                storemgr = getAdapter(self.context, IDataStoreFactory).create()
                storemgr.delete(credentials)
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
