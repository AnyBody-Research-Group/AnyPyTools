# coding: utf-8
"""
Adaapted from https://stackoverflow.com/a/56632466

This module provides a JobPopen class that is a subclass of the Popen class from the subprocess module.

"""

import subprocess
from subprocess import Popen
from threading import RLock

import win32api
import win32job
import win32process
import pywintypes

__all__ = ["JobPopen"]


class JobPopen(Popen):
    """Start a process in a new Win32 job object.

    This `subprocess.Popen` subclass takes the same arguments as Popen and
    behaves the same way. In addition to that, created processes will be
    assigned to a new anonymous Win32 job object on startup, which will
    guarantee that the processes will be terminated by the OS as soon as
    either the Popen object, job object handle or parent Python process are
    closed.
    """

    class _winapijobhandler(object):
        """Patches the native CreateProcess function in the subprocess module
        to assign created threads to the given job"""

        def __init__(self, oldapi, job):
            self._oldapi = oldapi
            self._job = job

        def __getattr__(self, key):
            if key != "CreateProcess":
                return getattr(self._oldapi, key)  # Any other function is run as before
            else:
                return self.CreateProcess  # CreateProcess will call the function below

        def CreateProcess(self, *args, **kwargs):
            hp, ht, pid, tid = self._oldapi.CreateProcess(*args, **kwargs)
            try:
                win32job.AssignProcessToJobObject(self._job, hp)
            except BaseException as e:  # to catch pywintypes.error
                if e.args == (6, "AssignProcessToJobObject", "The handle is invalid."):
                    # Try to ignore an error can occur randomly sometimes.
                    pass
                else:
                    raise e
            win32process.ResumeThread(ht)
            return hp, ht, pid, tid

    def __init__(self, *args, **kwargs):
        """Start a new process using an anonymous job object. Takes the same arguments as Popen"""

        # Create a new job object
        self._win32_job = self._create_job_object()

        # Temporarily patch the subprocess creation logic to assign created
        # processes to the new job, then resume execution normally.
        CREATE_SUSPENDED = 0x00000004
        kwargs.setdefault("creationflags", 0)
        kwargs["creationflags"] |= CREATE_SUSPENDED
        with RLock():
            _winapi = subprocess._winapi  # Python 3
            _winapi_key = "_winapi"
            try:
                setattr(
                    subprocess,
                    _winapi_key,
                    JobPopen._winapijobhandler(_winapi, self._win32_job),
                )
                super(JobPopen, self).__init__(*args, **kwargs)
            finally:
                setattr(subprocess, _winapi_key, _winapi)

    def _create_job_object(self):
        """Create a new anonymous job object"""
        hjob = win32job.CreateJobObject(None, "")
        extended_info = win32job.QueryInformationJobObject(
            hjob, win32job.JobObjectExtendedLimitInformation
        )
        extended_info["BasicLimitInformation"][
            "LimitFlags"
        ] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(
            hjob, win32job.JobObjectExtendedLimitInformation, extended_info
        )
        return hjob

    def _close_job_object(self, hjob):
        """Close the handle to a job object, terminating all processes inside it"""
        if self._win32_job:
            win32api.CloseHandle(self._win32_job)
            self._win32_job = None

    # This ensures that no remaining subprocesses are found when the process
    # exits from a `with JobPopen(...)` block.
    def __exit__(self, exc_type, value, traceback):
        super(JobPopen, self).__exit__(exc_type, value, traceback)
        self._close_job_object(self._win32_job)

    # Python does not keep a reference outside of the parent class when the
    # interpreter exits, which is why we keep it here.
    _Popen = subprocess.Popen

    def __del__(self):
        self._Popen.__del__(self)
        self._close_job_object(self._win32_job)
