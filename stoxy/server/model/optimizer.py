from __future__ import absolute_import

import os
import datetime

from zope.component import provideSubscriptionAdapter
from zope import schema
from zope.interface import Interface, implements

from grokcore.component import context

from opennode.oms.model.model.byname import ByNameContainerExtension
from opennode.oms.model.model.base import Model, IDisplayName, ContainerInjector, ReadonlyContainer
from opennode.oms.model.model.root import OmsRoot


OPTIMIZER_PATH = '/opt/optimizers'


class IOptimizer(Interface):
    name = schema.TextLine(title=u"Optimizer name", min_length=1)
    mtime = schema.TextLine(title=u"Last modification time", readonly=True, required=False)
    size = schema.TextLine(title=u"Size of a file", readonly=True, required=False)


class Optimizer(Model):
    implements(IOptimizer, IDisplayName)

    def __init__(self, name, stat_info):
        self.__name__ = name
        self.name = name
        self.mtime = datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(' ')
        self.size = stat_info.st_size

    def display_name(self):
        return self.name

    @property
    def nicknames(self):
        return [self.name]


class Optimizers(ReadonlyContainer):
    __name__ = 'optimizers'

    @property
    def _items(self):
        optimizers = {}
        for i in os.listdir(OPTIMIZER_PATH):
            stat_info = os.stat(os.path.join(OPTIMIZER_PATH, i))
            optimizers[i] = Optimizer(i, stat_info)
        return optimizers


class OptimizersRootInjector(ContainerInjector):
    context(OmsRoot)
    __class__ = Optimizers


provideSubscriptionAdapter(ByNameContainerExtension, adapts=(Optimizers, ))
