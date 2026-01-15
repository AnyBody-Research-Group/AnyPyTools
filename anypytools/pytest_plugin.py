# -*- coding: utf-8 -*-
# pylint: disable=no-member, unused-wildcard-import
"""
Created on Mon Sep  1 12:44:36 2014.

@author: Morten
"""
import os
import re
import ast
import time
import shutil
import warnings
import argparse
import itertools
import contextlib
import collections
from pathlib import Path
from traceback import format_list, extract_tb

import pytest

# from _pytest.fixtures import FixtureRequest
# from _pytest.fixtures import TopRequest


from pytest import TempPathFactory

from anypytools import AnyPyProcess, macro_commands
from anypytools.tools import (
    ON_WINDOWS,
    get_anybodycon_path,
    replace_bm_constants,
    get_bm_constants,
    anybodycon_version,
    find_ammr_path,
    get_ammr_version,
    winepath,
    wraptext,
    AMSVersion,
)

__all__ = [
    "AnyTestFile",
    "AnyTestItem",
    "AnyException",
    "AnyTestSession",
]


DEFAULT_ANYTEST_OUTPUT = Path.cwd() / "anytest-output"

LOAD_TIME_VARIABLE = "Global.System.LoadedModel.LoadDurationCPUThread"
RUN_TEST_TIME_VARIABLE = "Main.RunTest.RunDurationCPUThread"


def _is_load_duration_supported():
    return AMSVersion.from_string(pytest.anytest.ams_version) >= (7, 5, 0, 10759)


class AnyTestSession(object):
    """Class for storing configuation of the AnyTest plugin to pytest."""

    def __init__(self):
        self.ammr_version = ""
        self.ams_version = ""
        self.save_basefolder = ""
        self.anytest_compare_dir = ""
        self.last_number = None
        self.last_session = None

    def configure(self, config):
        """Configure the AnyTestSession object.

        This can't be in __init__()
        since it is instantiated and added to the pytest namespace very
        early in the pytest startup.
        """

        ammr_path = find_ammr_path(config.getoption("--ammr") or config.rootdir)
        self.ammr_version = get_ammr_version(ammr_path)
        self.ams_path = config.getoption("--anybodycon") or get_anybodycon_path()
        self.ams_path = os.path.abspath(self.ams_path) if self.ams_path else ""
        self.ams_version = anybodycon_version(self.ams_path)
        major_ammr_ver = 1 if self.ammr_version.startswith("1") else 2
        self.bm_constants_map = get_bm_constants(
            ammr_path=ammr_path, ammr_version=major_ammr_ver
        )


def _limited_traceback(excinfo):
    """Return a formatted traceback with this frame up removed.

    The function removes all the stack from this frame up
    (i.e from __file__ and up)
    """
    tb = extract_tb(excinfo.tb)
    try:
        idx = [__file__ in e for e in tb].index(True)
        return format_list(tb[idx + 1 :])
    except ValueError:
        return format_list(tb)


def _read_header(fpath):
    """Read the commented header of anyscript test file.

    The function remvoes any leading '//' comments.
    """
    code = ""
    with open(fpath) as f:
        for line in f.readlines():
            if line.startswith("//"):
                line = line.strip("//")
                code += line
            else:
                break
    return code


@contextlib.contextmanager
def change_dir(path):
    """Context manager for changing directories."""
    path = Path(path)
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def pytest_collect_file(parent, file_path):
    """Collect AnyScript test files."""
    if file_path.suffix.lower() == ".any" and file_path.stem.lower().startswith(
        "test_"
    ):
        return AnyTestFile.from_parent(parent, path=file_path)


def _format_switches(defs):
    if isinstance(defs, dict):
        defs = [defs]
    elif isinstance(defs, tuple):
        combinations = list(itertools.product(*defs))
        defs = []
        for elem in combinations:
            defs.append({k: v for d in elem for k, v in d.items()})
    elif isinstance(defs, list):
        pass
    else:
        defs = [dict()]
    if len(defs) == 0:
        defs = [dict()]
    return defs


def _as_absolute_paths(d, start=os.getcwd()):
    import ntpath as os_path

    start = str(start)
    out = {}
    start = start if ON_WINDOWS else winepath(start, "-w")
    for key, val in d.items():
        val = val if ON_WINDOWS else winepath(val, "-w")
        out[key] = os_path.abspath(os_path.relpath(val, start))
    return out


HEADER_ENSURES = (
    ("define", (dict, collections.abc.Sequence)),
    ("path", (dict, collections.abc.Sequence)),
    ("ignore_errors", (collections.abc.Sequence,)),
    ("warnings_to_include", (collections.abc.Sequence,)),
    ("fatal_warnings", (bool, collections.abc.Sequence)),
    ("keep_logfiles", (bool,)),
    ("logfile_prefix", (str,)),
    ("expect_errors", (collections.abc.Sequence,)),
    ("save_study", (str, collections.abc.Sequence, type(None))),
    ("pytest_markers", (collections.abc.Sequence,)),
    ("use_gui", (bool,)),
)


def _parse_header(header, test_file):
    ns = {"self": test_file}
    try:
        exec(header, globals(), ns)
    except SyntaxError:
        pass
    # Remove test-file object from namespace since it should not be passed on
    ns.pop("self", None)
    for name, types in HEADER_ENSURES:
        if name in ns and not isinstance(ns[name], types):
            typestr = ", ".join([t.__name__ for t in types])
            msg = f"{name} must be one of the following type(s) ({typestr})"
            raise TypeError(msg)
    return ns


def _write_macro_file(path, name, macro):
    filename = os.path.join(path, name + ".anymcr")
    with open(filename, "w") as f:
        f.writelines([str(mcr) + "\n" for mcr in macro])
    return filename


def _print_version_info():
    """Print the AnyBodyCon executable used in the test."""
    print("\nUsing:")
    print("  AnyBodyCon: ", pytest.anytest.ams_path)
    print("              ", anybodycon_version(pytest.anytest.ams_path))


def pytest_collection_finish(session):
    print()
    _print_version_info()
    print()


class DeferPlugin(object):
    """Simple plugin to defer pytest-xdist hook functions."""

    def pytest_xdist_setupnodes(self, config, specs):
        """called before any remote node is set up."""
        _print_version_info()


def pytest_configure(config):
    """Configure the AnyTest framework."""
    pytest.anytest = AnyTestSession()
    pytest.anytest.configure(config)

    if config.pluginmanager.hasplugin("xdist"):
        config.pluginmanager.register(DeferPlugin())


def pytest_collection_modifyitems(items, config):
    selected_items = []
    deselected_items = []
    if (
        config.getoption("--anytest-deselect")
        and config.getoption("--anytest-output") is not None
    ):
        # Deselect all test items which doesn't save data.
        for item in items:
            if getattr(item, "hdf5_outputs", False):
                selected_items.append(item)
            else:
                deselected_items.append(item)
        config.hook.pytest_deselected(items=deselected_items)
        items[:] = selected_items


class AnyTestFile(pytest.File):
    """pytest.File subclass for AnyScript files."""

    def collect(self):
        """Yield test cases from a AnyScript test file."""

        # Collect define statements from the header
        strheader = _read_header(self.path)
        header = _parse_header(strheader, test_file=self)
        def_list = _format_switches(header.pop("define", None))
        def_list = [
            replace_bm_constants(d, pytest.anytest.bm_constants_map) for d in def_list
        ]
        path_list = _format_switches(header.pop("path", None))
        combinations = itertools.product(def_list, path_list)
        # Run though the defines an create a test case for each
        for i, (any_defs, any_paths) in enumerate(combinations):
            if isinstance(any_defs, dict) and isinstance(any_paths, dict):
                yield AnyTestItem.from_parent(
                    name=self.path.stem,
                    id=i,
                    parent=self,
                    any_defs=any_defs,
                    any_paths=any_paths,
                    **header,
                )
            else:
                raise ValueError("Malformed input: ", header)


class AnyTestItem(pytest.Item):
    """pytest.Item subclass representing individual collected tests."""

    def __init__(self, name, id, parent, any_defs, any_paths, **kwargs):
        test_name = f"{name}_{id}"
        super().__init__(test_name, parent)
        self.any_defs = any_defs
        for k, v in self.config.getoption("define_kw") or {}:
            self.any_defs[k] = v
        self.any_defs["TEST_NAME"] = f'"{test_name}"'
        if self.config.getoption("--ammr"):
            any_paths["AMMR_PATH"] = self.config.getoption("--ammr")
            any_paths["ANYBODY_PATH_AMMR"] = self.config.getoption("--ammr")
        self.any_paths = _as_absolute_paths(any_paths, start=self.config.rootdir)
        self.name = test_name
        self.expect_errors = kwargs.get("expect_errors", [])

        for marker in kwargs.get("pytest_markers", []):
            self.add_marker(marker)

        self.timeout = self.config.getoption("--timeout")
        self.errors = []
        mainfile = self.path
        if not ON_WINDOWS:
            mainfile = winepath(mainfile, "-w")
        self.macro = [
            macro_commands.Load(mainfile, self.any_defs, self.any_paths),
        ]

        if _is_load_duration_supported():
            self.macro += [
                macro_commands.Dump(LOAD_TIME_VARIABLE),
            ]

        fatal_warnings = kwargs.get("fatal_warnings", False)
        warnings_to_include = kwargs.get("warnings_to_include", None)
        if warnings_to_include:
            warnings.warn(
                f"\n{name}:`warnings_to_include` is deprecated. \nSpecify the `fatal_warnings` variable as "
                "a list to select specific warnings",
                DeprecationWarning,
            )
            if not isinstance(fatal_warnings, collections.abc.Sequence):
                fatal_warnings = warnings_to_include

        if not isinstance(fatal_warnings, collections.abc.Sequence):
            fatal_warnings = ["WARNING"] if fatal_warnings else []

        self.app_opts = {
            "silent": True,
            "debug_mode": self.config.getoption("--anybody_debug_mode"),
            "anybodycon_path": pytest.anytest.ams_path,
            "timeout": self.timeout,
            "ignore_errors": kwargs.get("ignore_errors", []),
            "warnings_to_include": fatal_warnings,
            "fatal_warnings": bool(fatal_warnings),
            "keep_logfiles": kwargs.get("keep_logfiles", True),
            "logfile_prefix": kwargs.get("logfile_prefix", None),
            "use_gui": kwargs.get("use_gui", False),
        }
        if not self.config.getoption("--only-load"):
            self.macro += [macro_commands.RunOperation("Main.RunTest")]

        if _is_load_duration_supported():
            self.macro += [
                macro_commands.Dump(RUN_TEST_TIME_VARIABLE),
            ]

        self.hdf5_outputs = []
        save_study = kwargs.get("save_study", None)
        if save_study and self.config.getoption("--anytest-output") is not None:
            save_study = [save_study] if isinstance(save_study, str) else save_study
            for study in save_study:
                fname = f"{study}.anydata.h5"
                self.macro.append(
                    f'classoperation {study}.Output "Save data" --type="Deep" --file="{fname}"'
                )
                self.hdf5_outputs.append(fname)
        return

    # def setup(self) -> None:
    #     def func() -> None:
    #         pass

    #     self.funcargs = {}  # type: ignore[attr-defined]
    #     fm = self.session._fixturemanager
    #     self._fixtureinfo = fm.getfixtureinfo(  # type: ignore[attr-defined]
    #         node=self, func=func, cls=None, funcargs=False
    #     )
    #     self.fixture_request = FixtureRequest(self, _ispytest=True)
    #     self.fixture_request._fillfixtures()

    def runtest(self):
        """Run an AnyScript test item."""

        tmpdir = TempPathFactory.from_config(self.config, _ispytest=True).mktemp(
            self.name
        )

        with change_dir(tmpdir):
            self.app = AnyPyProcess(**self.app_opts)
            if ON_WINDOWS:
                result = self.app.start_macro(
                    self.macro, logfile=Path(self.name).with_suffix(".txt")
                )[0]
            else:
                # Disable caputure on linux due to a bug when AMS lauches it own python
                capmanager = self.config.pluginmanager.getplugin("capturemanager")
                with capmanager.global_and_fixture_disabled():
                    result = self.app.start_macro(
                        self.macro, logfile=Path(self.name).with_suffix(".txt")
                    )[0]

        if _is_load_duration_supported():
            load_time = result.get(LOAD_TIME_VARIABLE, None)
            if load_time is not None:
                self.user_properties.append(("Load time", load_time))

            run_test_time = result.get(RUN_TEST_TIME_VARIABLE, None)
            if run_test_time is not None:
                self.user_properties.append(("Run time", run_test_time))

        # Ignore error due to missing Main.RunTest
        if "ERROR" in result:
            runtest_missing = any("Main.RunTest" in err for err in result["ERROR"])
            if runtest_missing:
                runtest_errros = (
                    "Main.RunTest : Unresolved",
                    "Main.RunTest : Select Operation",
                    "run : command unexpected while",
                    "Main.RunTest.RunDurationCPUThread : Unresolved object",
                )
                result["ERROR"][:] = [
                    err
                    for err in result["ERROR"]
                    if not any(s in err for s in runtest_errros)
                ]
        # Check that the expected errors are present
        error_list = result.get("ERROR", [])
        if self.expect_errors:
            for xerr in self.expect_errors:
                xerr_found = False
                for error in error_list[:]:
                    if xerr in error:
                        xerr_found = True
                        error_list.remove(error)
                if not xerr_found:
                    self.errors.append(
                        f'TEST ERROR: Expected error not found: "{xerr}"'
                    )

        # Add remaining errors to item's error list
        if error_list:
            self.errors.extend(error_list)

        if self.errors:
            self.logfile = Path(result["task_work_dir"]) / result["task_logfile"]

        # Add info to the hdf5 file if compare output was set
        if self.hdf5_outputs:
            base = Path(
                self.config.getoption("--anytest-output") or DEFAULT_ANYTEST_OUTPUT
            )
            subfolder = Path(self.config.getoption("--anytest-name"))
            target = base / subfolder / self.name
            self.save_output_files(tmpdir, target, result, self.hdf5_outputs)

        if self.errors and self.config.getoption("--create-macros"):
            logfile = Path(result["task_logfile"])
            shutil.copy(logfile, self.path.parent)
            shutil.copy(logfile.with_suffix(".anymcr"), self.path.parent)

        # shutil.rmtree(tmpdir, ignore_errors=True)

        if len(self.errors) > 0:
            raise AnyException(self)

        return

    def save_output_files(self, src_folder, target_folder, result, hdf5files):
        """Saves hdf5, macro, and log files from a test run
        and copy it to the target_folder
        """
        import h5py

        target_folder = Path(target_folder)
        src_folder = Path(src_folder)
        src_log = src_folder / Path(result["task_logfile"]).name

        if target_folder.exists():
            shutil.rmtree(target_folder)
        os.makedirs(target_folder)

        for fn in hdf5files:
            if (src_folder / fn).exists():
                shutil.copyfile(src_folder / fn, target_folder / fn)
                f = h5py.File(target_folder / fn, "a")
                f.attrs["anytest_processtime"] = result["task_processtime"]
                f.attrs["anytest_macro"] = "\n".join(result["task_macro"][:-1])
                f.attrs["anytest_ammr_version"] = pytest.anytest.ammr_version
                f.attrs["anytest_ams_version"] = pytest.anytest.ams_version
                f.close()
            else:
                self.errors.append(f"ERROR: No HDF5 data were saved: {fn}")

        target_log = target_folder / "logfile.txt"
        shutil.copyfile(src_log, target_log)

    def repr_failure(self, excinfo):
        """Print a representation when a test failes."""
        if isinstance(excinfo.value, AnyException):
            rtn = "Main file:\n"
            rtn += wraptext(self.path, initial_indent="  ")
            rtn += "\nSpecial model configuration:"
            for k, v in self.any_defs.items():
                rtn += f"\n  #define {k} {v}"
            for k, v in self.any_paths.items():
                rtn += f"\n  #path {k} {v}"
            rtn += "\nErrors:"
            for elem in self.errors:
                rtn += "\n"
                rtn += wraptext(elem, initial_indent="> ", subsequent_indent="  ")
            rtn += f'\nFull logfile: "{self.logfile.absolute()}"'
            return rtn
        else:
            return str(excinfo.value)

    def reportinfo(self):
        """ """
        return self.path, 0, f"AnyBody Simulation: {self.name}"


class AnyException(Exception):
    """Custom exception for error reporting."""


def split_string_eq_1(kv):
    return kv.split("=", 1)


def pytest_addoption(parser):
    group = parser.getgroup("anypytools", "testing AnyBody models")

    group.addoption(
        "--anybodycon",
        action="store",
        metavar="path",
        help="anybodycon.exe used in test: default or " "path-to-anybodycon",
    )
    group.addoption(
        "--anybody_debug_mode",
        default=0,
        type=int,
        help="Sets the debug mode for the anybody console application. This can be used to enable crash dumps.",
    )
    group.addoption(
        "--only-load",
        action="store_true",
        help="Only run a load test. I.e. do not run the " "'RunTest' macro",
    )
    group.addoption(
        "--ammr",
        action="store",
        metavar="path",
        help="Can be used to specify which AnyBody Managed Model "
        "Repository (AMMR) to use. Setting this will pass a "
        "'AMMR_PATH' path statement for all models",
    )
    group.addoption(
        "--define",
        action="append",
        type=split_string_eq_1,
        dest="define_kw",
        help="Add custom define statements parse to all AnyScript models. "
        "Must be given in the form: --define MYDEF=6",
    )
    group._addoption(
        "--timeout",
        default=3600,
        type=int,
        help="terminate tests after a certain timeout period",
    )

    group.addoption(
        "--create-macros",
        action="store_true",
        help="Create a macro file if the test fails. This makes it "
        "easy to re-run the failed test in the gui application.",
    )
    group.addoption(
        "--anytest-name",
        nargs="?",
        default=time.strftime("%Y_%m_%d-%H.%M.%S"),
        help="Specify the subfolder where test output is stored. This defaults to a time stamp, but can overriden with a specific name",
    )

    group.addoption(
        "--anytest-deselect",
        dest="anytest_deselect",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Will deselect any test which does not produce hdf5 output.",
    )

    group.addoption(
        "--anytest-output",
        metavar="path",
        nargs="?",
        default=None,
        const=str(DEFAULT_ANYTEST_OUTPUT),
        help=(
            "Specify if hdf5 files are saved from the tests. Can be assined a value to specify the base "
            "folder where data will be saved. Default save directory is %(const)r."
        ),
    )
