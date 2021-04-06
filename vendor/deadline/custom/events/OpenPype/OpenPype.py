import Deadline.Events
import Deadline.Scripting


def GetDeadlineEventListener():
    return OpenPypeEventListener()


def CleanupDeadlineEventListener(eventListener):
    eventListener.Cleanup()


class OpenPypeEventListener(Deadline.Events.DeadlineEventListener):
    """
        Called on every Deadline plugin event, used for injecting OpenPype
        environment variables into rendering process.

        Expects that job already contains env vars:
                 AVALON_PROJECT
                 AVALON_ASSET
                 AVALON_TASK
                 AVALON_APP_NAME
        Without these only global environment would be pulled from OpenPype

        Configure 'Path to OpenPype executable dir' in Deadlines
            'Tools > Configure Events > openpype '
        Only directory path is needed.

    """
    def __init__(self):
        self.OnJobSubmittedCallback += self.OnJobSubmitted
        self.OnJobStartedCallback += self.OnJobStarted
        self.OnJobFinishedCallback += self.OnJobFinished
        self.OnJobRequeuedCallback += self.OnJobRequeued
        self.OnJobFailedCallback += self.OnJobFailed
        self.OnJobSuspendedCallback += self.OnJobSuspended
        self.OnJobResumedCallback += self.OnJobResumed
        self.OnJobPendedCallback += self.OnJobPended
        self.OnJobReleasedCallback += self.OnJobReleased
        self.OnJobDeletedCallback += self.OnJobDeleted
        self.OnJobErrorCallback += self.OnJobError
        self.OnJobPurgedCallback += self.OnJobPurged

        self.OnHouseCleaningCallback += self.OnHouseCleaning
        self.OnRepositoryRepairCallback += self.OnRepositoryRepair

        self.OnSlaveStartedCallback += self.OnSlaveStarted
        self.OnSlaveStoppedCallback += self.OnSlaveStopped
        self.OnSlaveIdleCallback += self.OnSlaveIdle
        self.OnSlaveRenderingCallback += self.OnSlaveRendering
        self.OnSlaveStartingJobCallback += self.OnSlaveStartingJob
        self.OnSlaveStalledCallback += self.OnSlaveStalled

        self.OnIdleShutdownCallback += self.OnIdleShutdown
        self.OnMachineStartupCallback += self.OnMachineStartup
        self.OnThermalShutdownCallback += self.OnThermalShutdown
        self.OnMachineRestartCallback += self.OnMachineRestart

    def Cleanup(self):
        del self.OnJobSubmittedCallback
        del self.OnJobStartedCallback
        del self.OnJobFinishedCallback
        del self.OnJobRequeuedCallback
        del self.OnJobFailedCallback
        del self.OnJobSuspendedCallback
        del self.OnJobResumedCallback
        del self.OnJobPendedCallback
        del self.OnJobReleasedCallback
        del self.OnJobDeletedCallback
        del self.OnJobErrorCallback
        del self.OnJobPurgedCallback

        del self.OnHouseCleaningCallback
        del self.OnRepositoryRepairCallback

        del self.OnSlaveStartedCallback
        del self.OnSlaveStoppedCallback
        del self.OnSlaveIdleCallback
        del self.OnSlaveRenderingCallback
        del self.OnSlaveStartingJobCallback
        del self.OnSlaveStalledCallback

        del self.OnIdleShutdownCallback
        del self.OnMachineStartupCallback
        del self.OnThermalShutdownCallback
        del self.OnMachineRestartCallback

    def set_openpype_executable_path(self, job):
        """
            Sets configurable OpenPypeExecutable value to job extra infos.

            GlobalJobPreLoad takes this value, pulls env vars for each task
            from specific worker itself. GlobalJobPreLoad is not easily
            configured, so we are configuring Event itself.
        """
        openpype_execs = self.GetConfigEntryWithDefault("OpenPypeExecutable",
                                                        "")
        job.SetJobExtraInfoKeyValue("openpype_executables", openpype_execs)

        Deadline.Scripting.RepositoryUtils.SaveJob(job)

    def updateFtrackStatus(self, job, statusName, createIfMissing=False):
        """Updates version status on ftrack"""
        pass

    def OnJobSubmitted(self, job):
        # self.LogInfo("OnJobSubmitted LOGGING")
        # for 1st time submit
        self.set_openpype_executable_path(job)
        self.updateFtrackStatus(job, "Render Queued")

    def OnJobStarted(self, job):
        # self.LogInfo("OnJobStarted")
        self.set_openpype_executable_path(job)
        self.updateFtrackStatus(job, "Rendering")

    def OnJobFinished(self, job):
        # self.LogInfo("OnJobFinished")
        self.updateFtrackStatus(job, "Artist Review")

    def OnJobRequeued(self, job):
        # self.LogInfo("OnJobRequeued LOGGING")
        self.set_openpype_executable_path(job)

    def OnJobFailed(self, job):
        pass

    def OnJobSuspended(self, job):
        # self.LogInfo("OnJobSuspended LOGGING")
        self.updateFtrackStatus(job, "Render Queued")

    def OnJobResumed(self, job):
        # self.LogInfo("OnJobResumed LOGGING")
        self.set_openpype_executable_path(job)
        self.updateFtrackStatus(job, "Rendering")

    def OnJobPended(self, job):
        # self.LogInfo("OnJobPended LOGGING")
        pass

    def OnJobReleased(self, job):
        pass

    def OnJobDeleted(self, job):
        pass

    def OnJobError(self, job, task, report):
        # self.LogInfo("OnJobError LOGGING")
        pass

    def OnJobPurged(self, job):
        pass

    def OnHouseCleaning(self):
        pass

    def OnRepositoryRepair(self, job, *args):
        pass

    def OnSlaveStarted(self, job):
        # self.LogInfo("OnSlaveStarted LOGGING")
        pass

    def OnSlaveStopped(self, job):
        pass

    def OnSlaveIdle(self, job):
        pass

    def OnSlaveRendering(self, host_name, job):
        # self.LogInfo("OnSlaveRendering LOGGING")
        pass

    def OnSlaveStartingJob(self, host_name, job):
        # self.LogInfo("OnSlaveStartingJob LOGGING")
        self.set_openpype_executable_path(job)

    def OnSlaveStalled(self, job):
        pass

    def OnIdleShutdown(self, job):
        pass

    def OnMachineStartup(self, job):
        pass

    def OnThermalShutdown(self, job):
        pass

    def OnMachineRestart(self, job):
        pass
