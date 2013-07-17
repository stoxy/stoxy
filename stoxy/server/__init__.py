from grokcore.component import implements, Subscription, context

import stoxy

from opennode.oms.config import IRequiredConfigurationFiles, gen_config_file_names
from opennode.oms.model.model import creatable_models
from opennode.oms.model.model.plugins import IPlugin, PluginInfo


class StoxyRequiredConfigurationFiles(Subscription):
    implements(IRequiredConfigurationFiles)
    context(object)

    def config_file_names(self):
        return gen_config_file_names(stoxy.server, 'stoxy')


class StoxyPlugin(PluginInfo):
    implements(IPlugin)

    def initialize(self):
        print "[StoxyPlugin] initializing plugin"

