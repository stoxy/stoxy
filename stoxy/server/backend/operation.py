from zope.interface import Interface


class IAction(Interface):

    def execute():
        pass
