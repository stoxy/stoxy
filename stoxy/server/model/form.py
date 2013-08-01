import copy

from opennode.oms.model.form import RawDataApplier
from opennode.oms.model.form import RawDataValidatingFactory
from opennode.oms.model.form import UnknownAttribute

from stoxy.server.model.dataobject import DataObject


class CdmiRawDataBuilder(RawDataValidatingFactory):

    ignored_attributes = tuple()

    def ignore_known_attributes(self, pair):
        attr, error = pair
        if isinstance(error, UnknownAttribute):
            if attr in self.ignored_attributes:
                return False
        return True

    @property
    def errors(self):
        errors = super(CdmiRawDataBuilder, self).errors
        return filter(self.ignore_known_attributes, errors)

    def create(self):
        """ Creates an object just like RawDataValidatingFactory, but ignores unknown attributes """

        self._orig_data = self.data
        self.data = copy.copy(self._orig_data)
        for key in self.ignored_attributes:
            if key in self.data:
                del self.data[key]

        return super(CdmiRawDataBuilder, self).create()


class CdmiObjectRawDataBuilder(CdmiRawDataBuilder):
    ignored_attributes = ('valuetransferencoding',)


class CdmiRawDataApplier(RawDataApplier):

    ignored_attributes = tuple()

    def ignore_known_attributes(self, pair):
        attr, error = pair
        if isinstance(error, UnknownAttribute):
            if attr in self.known_attributes:
                return False
        return True

    @property
    def errors(self):
        errors = super(CdmiRawDataApplier, self).errors
        return filter(self.ignore_known_attributes, errors)


class CdmiObjectRawDataApplier(CdmiRawDataApplier):
    ignored_attributes = ('valuetransferencoding',)


class CdmiObjectValidatorFactory(object):

    creator_constructor_map = {DataObject: CdmiObjectRawDataBuilder}
    applier_constructor_map = {DataObject: CdmiObjectRawDataApplier}

    @classmethod
    def get_creator(cls, requested_class, data):
        return cls.creator_constructor_map.get(requested_class,
                                               CdmiRawDataBuilder)(data, requested_class)

    @classmethod
    def get_applier(cls, obj, data):
        return cls.applier_constructor_map.get(obj.type, CdmiRawDataApplier)(data, obj)
