from zope.interface import Interface


class IAction(Interface):

    def execute():
        pass


class ILocalBackend(Interface):
    """Marker for a local processing backend."""


class ITorqueBackend(Interface):
    """Marker for Torque-based processing backend."""


class ISubmitJob(IAction):
    """Submits jobs to a processing backend."""


class IGetStatus(IAction):
    """Retrieves job status from the processing backend."""


class IGetResult(IAction):
    """Retrieves job's result from the processing backend"""


class ICleanJob(IAction):
    """Cleans existing job files"""


class IArchive(IAction):
    """Archives job related data"""
