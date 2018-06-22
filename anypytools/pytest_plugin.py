# -*- coding: utf-8 -*-
# pylint: disable=no-member, unused-wildcard-import
"""
Created on Mon Sep  1 12:44:36 2014.

@author: Morten
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import *  # noqa

import os
import re
import ast
import shutil
import argparse
import itertools
import contextlib
from traceback import format_list, extract_tb

import pytest

from anypytools import AnyPyProcess, macro_commands
from anypytools.tools import (
    get_anybodycon_path,
    replace_bm_constants,
    get_bm_constants,
    anybodycon_version,
    find_ammr_path,
    get_tag,
    get_ammr_version,
    wraptext,
)


@contextlib.contextmanager
def cwd(path):
    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


class AnyTestSession(object):
    """Class for storing configuation of the AnyTest plugin to pytest."""

    def __init__(self):
        self.ammr_version = ""
        self.ams_version = ""
        self.save_basefolder = ""
        self.anytest_compare_dir = ""
        self.current_run_folder = None
        self.save_name = ""
        self.last_number = None
        self.last_session = None

    def configure(self, config):
        """Configure the AnyTestSession object.

        This can't be in __init__()
        since it is instantiated and added to the pytest namespace very
        early in the pytest startup.
        """
        self.save_basefolder = config.getoption("--anytest-storage")
        if not os.path.exists(self.save_basefolder):
            os.makedirs(self.save_basefolder)
        self.save_name = config.getoption("--anytest-save")
        if self.save_name == "":
            self.save_name == get_tag()
        self.save_name_study = config.getoption("--anytest-save-study")
        ammr_path = find_ammr_path(config.getoption("--ammr") or config.rootdir.strpath)
        self.ammr_version = get_ammr_version(ammr_path)
        self.ams_path = config.getoption("--anybodycon") or get_anybodycon_path()
        self.ams_path = os.path.abspath(self.ams_path) if self.ams_path else ""
        self.ams_version = anybodycon_version(self.ams_path)
        major_ammr_ver = 1 if self.ammr_version.startswith("1") else 2
        self.bm_constants_map = get_bm_constants(
            ammr_path=ammr_path, ammr_version=major_ammr_ver
        )

    def finalize(self, config):
        """Finalize a session."""
        if self.save_name:
            storage_folder = os.path.join(self.save_basefolder, self.save_name)
            shutil.rmtree(storage_folder, ignore_errors=True)
            if os.path.exists(self.current_run_folder):
                shutil.copytree(self.current_run_folder, storage_folder)

    def get_save_fname(self, name, id, study):
        """Return the name of the compare h5file, and ensure the parent folder exists."""
        # Initialize and empty the current_run folder.
        if not self.current_run_folder:
            self.current_run_folder = os.path.join(self.save_basefolder, "current_run")
            if os.path.exists(self.current_run_folder):
                shutil.rmtree(self.current_run_folder)
        if id > 0:
            compare_test_name = "{}_{}".format(name, id)
        else:
            compare_test_name = "{}".format(name)
        compare_test_folder = os.path.join(self.current_run_folder, compare_test_name)
        studyname = "{}.anydata.h5".format(study)
        return os.path.join(compare_test_folder, studyname)


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
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def pytest_collect_file(parent, path):
    """Collect AnyScript test files."""
    if path.ext.lower() == ".any" and path.basename.lower().startswith("test_"):
        return AnyFile(path, parent)


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
        defs = [{}]
    if len(defs) == 0:
        defs = [{}]
    return defs


def _as_absolute_paths(d, start=os.getcwd()):
    return {k: os.path.abspath(os.path.relpath(v, start)) for k, v in d.items()}


HEADER_ENSURES = (
    ("define", (dict, list, tuple)),
    ("path", (dict, list, tuple)),
    ("ignore_errors", (list,)),
    ("warnings_to_include", (list,)),
    ("fatal_warnings", (bool,)),
    ("keep_logfiles", (bool,)),
    ("logfile_prefix", (str,)),
    ("expect_errors", (list,)),
)


def _parse_header(header):
    ns = {}
    try:
        exec(header, globals(), ns)
    except SyntaxError:
        pass
    if len(ns) == 0:
        try:
            ns["define"] = ast.literal_eval(header)
        except SyntaxError:
            pass
    for name, types in HEADER_ENSURES:
        if name in ns and not isinstance(ns[name], types):
            typestr = ", ".join([t.__name__ for t in types])
            msg = "{} must be one of the following type(s) ({})".format(name, typestr)
            raise TypeError(msg)
    return ns


def pytest_collection_finish(session):
    """Print the AnyBodyCon executable used in the test."""
    print("\nUsing AnyBodyCon: ", pytest.anytest.ams_path)


def pytest_namespace():
    """Add an instance of the AnyTestSession class to the pytest name space."""
    return {"anytest": AnyTestSession()}


def pytest_configure(config):
    """Configure the AnyTest framework."""
    pytest.anytest.configure(config)


def pytest_unconfigure(config):
    """Finialize the test session."""
    pytest.anytest.finalize(config)


def write_macro_file(path, name, macro):
    """Write list of macros to a file."""
    filename = os.path.join(path, name + ".anymcr")
    with open(filename, "w") as f:
        f.writelines([str(mcr) + "\n" for mcr in macro])
    return filename


class AnyFile(pytest.File):
    """pytest.File subclass for AnyScript files."""

    def collect(self):
        """Yield test cases from a AnyScript test file."""
        # Collect define statements from the header
        strheader = _read_header(self.fspath.strpath)
        header = _parse_header(strheader)
        def_list = _format_switches(header.pop("define", {}))
        def_list = [
            replace_bm_constants(d, pytest.anytest.bm_constants_map) for d in def_list
        ]
        path_list = _format_switches(header.pop("path", {}))
        combinations = itertools.product(def_list, path_list)
        # Run though the defines an create a test case for each
        for i, (defs, paths) in enumerate(combinations):
            if isinstance(defs, dict) and isinstance(paths, dict):
                yield AnyItem(
                    name=self.fspath.basename,
                    id=i,
                    parent=self,
                    defs=defs,
                    paths=paths,
                    **header
                )
            else:
                raise ValueError("Malformed input: ", header)


class AnyItem(pytest.Item):
    """pytest.Item subclass representing individual collected tests."""

    def __init__(self, name, id, parent, defs, paths, **kwargs):
        test_name = "{}_{}".format(name, id)
        super().__init__(test_name, parent)
        self.defs = defs
        for k, v in self.config.getoption("define_kw") or {}:
            self.defs[k] = v
        self.defs["TEST_NAME"] = '"{}"'.format(test_name)
        if self.config.getoption("--ammr"):
            paths["AMMR_PATH"] = self.config.getoption("--ammr")
            paths["ANYBODY_PATH_AMMR"] = self.config.getoption("--ammr")
        self.paths = _as_absolute_paths(paths, start=self.config.rootdir.strpath)
        self.name = test_name
        self.expect_errors = kwargs.get("expect_errors", [])
        self.save_study = pytest.anytest.save_name_study
        if not self.save_study:
            self.save_study = kwargs.get("save_study", "Main.Study")
        self.timeout = self.config.getoption("--timeout")
        self.errors = []
        self.macro = [macro_commands.Load(self.fspath.strpath, self.defs, self.paths)]
        self.save_filename = None
        self.macro_file = None
        self.anybodycon_path = pytest.anytest.ams_path
        self.app_opts = {
            "return_task_info": True,
            "silent": True,
            "anybodycon_path": self.anybodycon_path,
            "timeout": self.timeout,
            "ignore_errors": kwargs.get("ignore_errors", []),
            "warnings_to_include": kwargs.get("warnings_to_include", []),
            "fatal_warnings": kwargs.get("fatal_warnings", False),
            "keep_logfiles": kwargs.get("keep_logfiles", False),
            "logfile_prefix": kwargs.get("logfile_prefix", None),
        }
        if not self.config.getoption("--only-load"):
            self.macro.append(macro_commands.OperationRun("Main.RunTest"))
        if pytest.anytest.save_name:
            # Add save operation to the test macro
            self.save_filename = pytest.anytest.get_save_fname(
                name, id, self.save_study
            )
            save_str = 'classoperation {}.Output "Save data" --type="Deep" --file="{}"'
            save_str = save_str.format(self.save_study, self.save_filename)
            self.macro.append(macro_commands.MacroCommand(save_str))

    def runtest(self):
        """Run an AnyScript test item."""
        tmpdir = self.config._tmpdirhandler.mktemp(self.name)
        if self.save_filename:
            os.makedirs(os.path.dirname(self.save_filename))
        with change_dir(tmpdir.strpath):
            app = AnyPyProcess(**self.app_opts)
            result = app.start_macro(self.macro)[0]
            self.app = app
        # Ignore error due to missing Main.RunTest
        if "ERROR" in result:
            for i, err in enumerate(result["ERROR"]):
                runtest_errros = (
                    "Error : Main.RunTest : Unresolved object",
                    "Main.RunTest : Select Operation is not expected",
                )
                if any(s in err for s in runtest_errros):
                    del result["ERROR"][i]
                    break
        # Check that the expected errors are present
        if self.expect_errors:
            error_list = result.get("ERROR", [])
            for xerr in self.expect_errors:
                xerr_found = False
                for i, error in enumerate(error_list):
                    if xerr in error:
                        xerr_found = True
                        del error_list[i]
                if not xerr_found:
                    self.errors.append(
                        "TEST ERROR: Expected error not " 'found: "{}"'.format(xerr)
                    )
        # Add remaining errors to item's error list
        if "ERROR" in result and len(result["ERROR"]) > 0:
            self.errors.extend(result["ERROR"])
        # Add info to the hdf5 file if compare output was set
        if self.save_filename is not None:
            import h5py

            f = h5py.File(self.save_filename, "a")
            f.attrs["anytest_processtime"] = result["task_processtime"]
            f.attrs["anytest_macro"] = "\n".join(result["task_macro"][:-1])
            f.attrs["anytest_ammr_version"] = pytest.anytest.ammr_version
            f.attrs["anytest_ams_version"] = pytest.anytest.ams_version
            f.close()
            basedir = os.path.dirname(self.save_filename)
            macrofile = write_macro_file(basedir, self.save_study, self.macro[:-1])
            with open(os.path.join(basedir, self.save_study + ".bat"), "w") as f:
                anybodygui = re.sub(
                    r"(?i)anybodycon\.exe", r"anybody\.exe", self.anybodycon_path
                )
                f.write('"{}" -m "{}"'.format(anybodygui, macrofile))

        if len(self.errors) > 0:
            if self.config.getoption("--create-macros"):
                macro_name = write_macro_file(
                    self.fspath.dirname, self.name, self.macro
                )
                self.macro_file = macro_name
            raise AnyException(self)
        return

    def repr_failure(self, excinfo):
        """Print a representation when a test failes."""
        if isinstance(excinfo.value, AnyException):
            rtn = "Main file:\n"
            rtn += wraptext(self.fspath.strpath, initial_indent="  ")
            rtn += "\nSpecial model configuration:"
            for k, v in self.defs.items():
                rtn += "\n  #define {} {}".format(k, v)
            for k, v in self.paths.items():
                rtn += "\n  #path {} {}".format(k, v)
            if self.macro_file is not None:
                macro_file = self.macro_file.replace(os.sep, os.altsep)
                rtn += "\nMacro:"
                rtn += wraptext(
                    '\n  anybody.exe -m "{}" &'.format(macro_file), initial_indent="  "
                )
            rtn += "\nErrors:"
            for elem in self.errors:
                rtn += "\n"
                rtn += wraptext(elem, initial_indent="> ", subsequent_indent="  ")
            return rtn
        else:
            return str(excinfo.value)

    def reportinfo(self):
        return self.fspath, 0, "AnyBody Simulation: %s" % self.name


class AnyException(Exception):
    """Custom exception for error reporting."""


def parse_save_name(stringval):
    """Parse function."""
    if not stringval:
        raise argparse.ArgumentTypeError("Argument can't be empty.")
    not_allowed = "".join(c for c in r"\/:*?<>|" if c in stringval)
    if not_allowed:
        raise argparse.ArgumentTypeError(
            "Characters are not allowed: " "/:*?<>|\\ (it has %r)" % not_allowed
        )
    return stringval


def pytest_addoption(parser):
    group = parser.getgroup("anypytools", "testing AnyBody models")

    group.addoption(
        "--anybodycon",
        action="store",
        metavar="path",
        help="anybodycon.exe used in test: default or " "path-to-anybodycon",
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
        "--only-load",
        action="store_true",
        help="Only run a load test. I.e. do not run the " "'RunTest' macro",
    )
    group.addoption(
        "--define",
        action="append",
        type=lambda kv: kv.split("=", 1),
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
        "--anytest-save",
        metavar="NAME",
        type=parse_save_name,
        help="Save the current run into folder " "`~/.anytest/counter-NAME/`.",
    )
    group.addoption(
        "--anytest-save-study",
        type=str,
        help="Used to specify the study saved by the --anytest-save option. "
        'Defaults to: "Main.Study" or what is set in the "test_*.any" file',
    )
    group.addoption(
        "--create-macros",
        action="store_true",
        help="Create a macro file if the test fails. This makes it "
        "easy to re-run the failed test in the gui application.",
    )
    group.addoption(
        "--anytest-storage",
        metavar="path",
        default=os.path.expanduser("~/.anytest"),
        help="Specify a path to store the runs (when --anytest-save "
        "are used). Default: %(default)r.",
    )

