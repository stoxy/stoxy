import json

from grokcore.component import context

from opennode.oms.model.form import RawDataValidatingFactory
from opennode.oms.endpoint.httprest.view import ContainerView
from opennode.oms.endpoint.httprest.base import IHttpRestView
from opennode.oms.endpoint.httprest.root import BadRequest

from stoxy.server.model.container import IDataContainer, DataContainer
from stoxy.server.model.dataobject import IDataObject, DataObject


class DataContainerView(ContainerView):
    context(IDataContainer)

    def render_PUT(self, request):
        try:
            data = json.load(request.content)
        except ValueError:
            raise BadRequest("Input data could not be parsed")

        if not isinstance(data, dict):
            raise BadRequest("Input data must be a dictionary")

        form = RawDataValidatingFactory(data, DataContainer)

        if not form.errors:
            form.apply()
            return [IHttpRestView(self.context).render_recursive(request, depth=0)]
        else:
            request.setResponseCode(BadRequest.status_code)
            return form.error_dict()


class DataObjectView(ContainerView):
    context(IDataObject)

    def render_PUT(self, request):
        try:
            data = json.load(request.content)
        except ValueError:
            raise BadRequest("Input data could not be parsed")

        if not isinstance(data, dict):
            raise BadRequest("Input data must be a dictionary")

        form = RawDataValidatingFactory(data, DataObject)

        if not form.errors:
            form.apply()
            return [IHttpRestView(self.context).render_recursive(request, depth=0)]
        else:
            request.setResponseCode(BadRequest.status_code)
            return form.error_dict()
