from grokcore.component import implements, Subscription, context

import stoxy

from opennode.oms.config import IRequiredConfigurationFiles, gen_config_file_names
from opennode.oms.model.model import creatable_models
from opennode.oms.model.model.plugins import IPlugin, PluginInfo

from stoxy.server.model.dataobject import DataObject
from stoxy.server.model.container import DataContainer


class StoxyRequiredConfigurationFiles(Subscription):
    implements(IRequiredConfigurationFiles)
    context(object)

    def config_file_names(self):
        return gen_config_file_names(stoxy.server, 'stoxy')


class StoxyPlugin(PluginInfo):
    implements(IPlugin)

    def initialize(self):
        print "[StoxyPlugin] initializing plugin"

        stoxy_creatable_models = dict((cls.__name__.lower(), cls)
                                        for cls in [DataObject, DataContainer])

        creatable_models.update(stoxy_creatable_models)


