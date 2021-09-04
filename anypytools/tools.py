# -*- coding: utf-8 -*-
"""
Created on Sun Sep  7 13:25:38 2014.

@author: Morten
"""
import os
import re
import sys
import xml
import copy
import errno
import shutil
import logging
import textwrap
import datetime
import warnings
import platform
import functools
import subprocess
import collections
import pprint
from ast import literal_eval
from pathlib import Path
from _thread import get_ident as _get_ident

from typing import Mapping, Optional, Sequence, Union

# external imports
import numpy as np

logger = logging.getLogger("abt.anypytools")


def run_from_ipython():
    try:
        __IPYTHON__
        return True
    except NameError:
        return False


ANYBODYCON_VERSION_RE = re.compile(
    r".*version\s:\s(?P<version>(?P<v1>\d)\.\s(?P<v2>\d)"
    r"\.\s(?P<v3>\d)\.\s(?P<build>\d+)\s\((?P<arc>.*)\))"
)

ON_WINDOWS = platform.system() == "Windows"


def case_preserving_replace(string, old, new):
    """Replace string while preserving the case"""

    def repl(match):
        current = match.group()
        result = ""
        all_upper = True
        for i, c in enumerate(current):
            if i >= len(new):
                break
            if c.isupper():
                result += new[i].upper()
            else:
                result += new[i].lower()
                all_upper = False
        # append any remaining characters from new
        if all_upper:
            result += new[i + 1 :].upper()
        else:
            result += new[i + 1 :].lower()
        return result

    regex = re.compile(re.escape(old), re.I)
    return regex.sub(repl, string)


@functools.lru_cache(maxsize=None)
def winepath(path, opts=None):
    """ " Wrapper for the winepath commandline tool"""
    if not opts:
        opts = ["-u"]
    if isinstance(opts, str):
        opts = [opts]
    try:
        out = subprocess.check_output(
            ["winepath", *opts, f"{path}"], universal_newlines=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return out.strip()


def anybodycon_version(anybodyconpath=None):
    """Return the AnyBodyCon version."""
    anybodyconpath = anybodyconpath or get_anybodycon_path()
    if anybodyconpath is None:
        return "0.0.0"
    cmd = [anybodyconpath, "-ni"]
    if not ON_WINDOWS:
        cmd.insert(0, "wine")
    out = subprocess.run(cmd, universal_newlines=True, stdout=subprocess.PIPE).stdout
    m = ANYBODYCON_VERSION_RE.search(out)
    if m:
        return m.groupdict()["version"]
    else:
        return "0.0.0"


AMMR_VERSION_RE = re.compile(r'.*AMMR_VERSION\s"(?P<version>.*)"')


def ammr_any_version(fpath):
    with open(fpath) as f:
        out = f.read()
    match = AMMR_VERSION_RE.search(out)
    if match:
        return match.groupdict()["version"]
    else:
        return "Unknown AMMR version"


def wraptext(elem, initial_indent="", subsequent_indent=None):
    """Wraps text to fit the terminal window."""
    width = 120
    if sys.version_info.major == 3:
        width = max(width, shutil.get_terminal_size().columns - 1)
    subsequent_indent = subsequent_indent or initial_indent
    return textwrap.fill(
        elem, width, initial_indent=initial_indent, subsequent_indent=subsequent_indent
    )


def amm_xml_version(fpath):
    try:
        tree = xml.etree.ElementTree.parse(fpath)
        version = tree.getroot()
        v1, v2, v3 = (
            version.find("v1").text,
            version.find("v2").text,
            version.find("v3").text,
        )
        return "{}.{}.{}".format(v1, v2, v3)
    except Exception:
        vstring = "Unknown AMMR version"
    return vstring


def find_ammr_path(folder=None):
    """Return the root AMMR path if possible .

    The function will walk up a directory tree looking
    for a ammr_verion.any file to parse.
    """
    folder = folder or os.getcwd()
    version_files = ("AMMR.version.any", "AMMR.version.xml")
    for basedir, _, files in walk_up(folder):
        if any(fn in files for fn in version_files):
            return basedir
    else:
        return None


def get_ammr_version(folder=None):
    """Return the AMMR version if possible.

    The function will walk up a directory tree looking
    for a ammr_verion.any file to parse.
    """
    folder = folder or os.getcwd()
    any_version_file = "AMMR.version.any"
    xml_version_file = "AMMR.version.xml"
    files = os.listdir(folder)
    if any_version_file in files:
        return ammr_any_version(os.path.join(folder, any_version_file))
    elif xml_version_file in files:
        return amm_xml_version(os.path.join(folder, xml_version_file))
    else:
        return ""


def walk_up(bottom):
    """Mimic os.walk, but walk 'up' instead of down the directory tree."""
    bottom = os.path.realpath(bottom)
    # get files in current dir
    names = os.listdir(bottom)
    dirs, nondirs = [], []
    for name in names:
        if os.path.isdir(os.path.join(bottom, name)):
            dirs.append(name)
        else:
            nondirs.append(name)
    yield bottom, dirs, nondirs
    new_path = os.path.realpath(os.path.join(bottom, ".."))
    # see if we are at the top
    if new_path == bottom:
        return
    for x in walk_up(new_path):
        yield x


def get_current_time():
    return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def get_tag(project_name=None):
    info = get_git_commit_info(project_name)
    parts = [info["id"], get_current_time()]
    if info["dirty"]:
        parts.append("uncommited-changes")
    return "_".join(parts)


def get_git_project_name():
    cmd = "git config --local remote.origin.url".split()
    try:
        output = subprocess.check_output(cmd, universal_newlines=True)
    except (subprocess.CalledProcessError, IOError):
        name = None
    else:
        name = re.findall(r"/([^/]*)\.git", output)[0]
    return name if name is not None else os.path.basename(os.getcwd())


def get_git_branch_info():
    """Return the branch name for git repository."""
    cmd = "git rev-parse --abbrev-ref HEAD"
    try:
        branch = subprocess.check_output(cmd, universal_newlines=True).strip()
    except (subprocess.CalledProcessError, IOError):
        branch = "unknown"
    else:
        if branch == "HEAD":
            return "(detached head)"
    return branch


def get_git_commit_info(project_name=None):
    dirty = False
    commit = "unversioned"
    project_name = project_name or get_git_project_name()
    branch = get_git_branch_info()
    cmd = "git describe --dirty --always --long --abbrev=6".split()
    try:
        output = subprocess.check_output(cmd, universal_newlines=True).strip()
    except (subprocess.CalledProcessError, IOError):
        pass
    else:
        try:
            output = output.split("-")
            if output[-1].strip() == "dirty":
                dirty = True
                output.pop()
            commit = output[-1].strip("g")
        except Exception:
            commit = "unknown"
    return dict(id=commit, dirty=dirty, project=project_name, branch=branch)


def _get_first_key_match(key, names):
    """Find the first partial match key match.

    If No match if found then key is returned unmodified.
    """
    if key in names:
        return key
    matching = [v for v in names if key in v]
    if not matching:
        # No match return original key.
        return key

    if len(matching) > 1:
        print(
            'WARNING: "{}" key is not unique.' " Using the first match".format(key),
            file=sys.stderr,
        )
        print("-> " + matching[0], file=sys.stderr)
        for match in matching[1:]:
            print(" * " + match, file=sys.stderr)

    return matching[0]


class AnyPyProcessOutputList(collections.abc.MutableSequence):
    """List like class to wrap the output of model simulations.

    The class behaves as a normal list but provide
    extra function to easily access data.
    """

    def __init__(self, *args):
        self.list = list()
        for elem in args:
            self.extend(list(elem))

    def check(self, v):
        if not isinstance(v, collections.abc.MutableSequence):
            v = [v]
        for e in v:
            if not isinstance(e, collections.OrderedDict):
                raise (TypeError(e))

    def __len__(self):
        return len(self.list)

    def __getitem__(self, i):
        if isinstance(i, str):
            # Find the entries where i matches the keys
            key = _get_first_key_match(i, self.list[0])
            try:
                data = np.array(
                    [super(AnyPyProcessOutput, e).__getitem__(key) for e in self.list]
                )
            except KeyError:
                msg = " The key: '{}' is not present in all elements of the output."
                raise KeyError(msg.format(key)) from None
            if data.dtype == np.dtype("O"):
                # Data will be stacked as an array of objects, if the length of the
                # time dimension is not consistant across simulations. Warn that some numpy
                # featurs will not be avaiable.
                warnings.warn(
                    "\nThe length of the time variable varies across macros. "
                    "Numpy does not support ragged arrays. Data is returned  "
                    "as an array of array objects"
                )
            return data
        else:
            return type(self)(self.list[i]) if isinstance(i, slice) else self.list[i]

    def __delitem__(self, i):
        del self.list[i]

    def __setitem__(self, i, v):
        self.check(v)
        if isinstance(i, slice):
            self.list[i] = v
        else:
            self.list[i] = v

    def insert(self, i, v):
        self.check(v)
        self.list.insert(i, v)

    def __str__(self):
        return str(self.list)

    def __repr__(self):
        def create_repr(maxlength=500):
            repr_list = []
            for elem in self.list:
                if not isinstance(elem, AnyPyProcessOutput):
                    repr_list.append("  " + pprint.pformat(elem))
                    continue
                for line in elem._repr_gen(prefix=" "):
                    repr_list.append(line)
                    if maxlength and len(repr_list) > maxlength:
                        repr_list.append("  ...")
                        return repr_list
                if repr_list and not repr_list[-1].endswith(","):
                    repr_list[-1] = repr_list[-1] + ","

            if len(repr_list):
                repr_list[-1] = repr_list[-1].rstrip(",")
                repr_list[0] = "[" + repr_list[0][1:]
                repr_list[-1] = repr_list[-1] + "]"
            else:
                repr_list.append("[]")
            return repr_list

        repr_str = "\n".join(create_repr(500))
        if repr_str.endswith("..."):
            np.set_printoptions(threshold=30)
            repr_str = "\n".join(create_repr(1000))
            np.set_printoptions()
        return repr_str

    def filter(self, function):
        """Filter elements for whichfunction returns true."""
        return AnyPyProcessOutputList(filter(function, self))

    def shelve(self, filename, key="results"):
        import shelve

        db = shelve.open(filename)
        db[key] = self
        db.close()

    @classmethod
    def from_shelve(cls, filename, key="results"):
        import shelve

        db = shelve.open(filename)
        out = db[key]
        db.close()
        return out

    def tolist(self):
        """Return as native python types (list of dicts)."""
        return [
            {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in elem.items()}
            for elem in self
        ]

    def to_dataframe(self, index_var="auto", **kwargs):
        """Return output of all simuations as a concatenated pandas dataframe.

        Parameters:
        -----------
        index_var: str
            Name of the variable to use as axis 0 in the dataframe.
            If not given system will look for variables ending with
            "Ouput.Abcsissa.t"
        interp_var: str
            Name of the variable on which the data is interpolating/resampled.
        interp_val: np.ndarray
            Values to use when re-interpolating/resampling the data.
        interp_method: str
            Method to use when re-interpolating/resampling the data. Defaults to 'cubic'.


        Returns:
        --------
        pandas.DataFrame
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for this function")

        dfs = [elem.to_dataframe(index_var, **kwargs) for elem in self]
        dfout = pd.concat(dfs, keys=range(len(dfs)), sort=False)
        if "task_id" in dfout.columns:
            dfout["task_id"] = pd.Categorical(dfout.task_id, ordered=True)
        return dfout


def _expand_short_path_name(short_path_name):
    from ctypes import create_unicode_buffer, windll

    BUFFER_SIZE = 500
    buffer = create_unicode_buffer(BUFFER_SIZE)
    get_long_path_name = windll.kernel32.GetLongPathNameW
    get_long_path_name(short_path_name, buffer, BUFFER_SIZE)
    long_path_name = buffer.value
    return long_path_name


def get_anybodycon_path():
    """Return the path to default AnyBody console application."""
    if not ON_WINDOWS:
        wineprefix = Path(os.environ.get("WINEPREFIX", Path.home() / ".wine"))
        abtpath = wineprefix / "drive_c/Program Files/AnyBody Technology"
        anybodycon_paths = list(abtpath.glob("*/AnyBodyCon.exe"))
        if anybodycon_paths:
            return str(anybodycon_paths[-1])
        else:
            return None
    try:
        import winreg
    except ImportError:
        import _winreg as winreg
    try:
        abpath = winreg.QueryValue(
            winreg.HKEY_CLASSES_ROOT, "AnyBody.AnyScript\\shell\\open\\command"
        )
    except WindowsError:
        raise WindowsError("Could not locate AnyBody in registry")
    abpath = abpath.rsplit(" ", 1)[0].strip('"')
    abpath = os.path.join(os.path.dirname(abpath), "AnyBodyCon.exe")
    if "~" in abpath:
        abpath = _expand_short_path_name(abpath)
    return abpath


def define2str(key, value=None):
    if isinstance(value, str):
        if value.startswith('"') and value.endswith('"'):
            defstr = '-def %s=---"\\"%s\\""' % (key, value[1:-1].replace("\\", "\\\\"))
        else:
            defstr = '-def %s="%s"' % (key, value)
    elif value is None:
        defstr = '-def %s=""' % (key)
    elif isinstance(value, float):
        defstr = '-def %s="%g"' % (key, value)
    else:
        defstr = '-def %s="%d"' % (key, value)
    return defstr


def path2str(key, path="."):
    return '-p %s=---"%s"' % (key, path.replace("\\", "\\\\"))


def getsubdirs(toppath, search_string="."):
    """Find all directories below a given top path.

    Args:
        toppath: top directory when searching for sub directories
        search_string: Limit to directories matching the this regular expression
    Returns:
        List of directories
    """
    if not search_string:
        return [toppath]
    reg_prog = re.compile(search_string)
    dirlist = []
    if search_string == ".":
        dirlist.append(toppath)
    for root, _, files in os.walk(toppath):
        for fname in files:
            if reg_prog.search(os.path.join(root, fname)):
                dirlist.append(root)
                continue
    uniqueList = []
    for value in dirlist:
        if value not in uniqueList:
            uniqueList.append(value)
    return uniqueList


def array2anyscript(arr):
    """Format a numpy array as an anyscript variable."""

    def tostr(v):
        # pylint: disable=no-member
        if np.isreal(v):
            return "{:.12g}".format(v)
        elif isinstance(v, (str, np.str_)):
            return '"{}"'.format(v)

    def createsubarr(arr):
        outstr = ""
        if isinstance(arr, np.ndarray):
            if len(arr) == 1 and not isinstance(arr[0], np.ndarray):
                return "{" + tostr(arr[0]) + "},"
            outstr += "{"
            for row in arr:
                outstr += createsubarr(row)
            outstr = outstr.strip(",") + "},"
            return outstr
        else:
            return outstr + tostr(arr) + ","

    if isinstance(arr, np.ndarray) and not arr.shape:
        return tostr(arr.tolist())
    elif isinstance(arr, np.ndarray):
        return createsubarr(arr).strip(",")
    elif isinstance(arr, float):
        return tostr(arr)
    else:
        return str(arr)


class AnyPyProcessOutput(collections.OrderedDict):
    """Subclassed OrderedDict which supports partial key access."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._task_info_in_repr = False

    def __getitem__(self, key):
        try:
            return super(AnyPyProcessOutput, self).__getitem__(key)
        except KeyError:
            key = _get_first_key_match(key, super(AnyPyProcessOutput, self).keys())

        try:
            return super(AnyPyProcessOutput, self).__getitem__(key)
        except KeyError:
            msg = "The key {} could not be found in the data".format(key)
            raise KeyError(msg) from None

    def _repr_gen(self, prefix):
        items = self.items()
        if not items:
            yield prefix + "{}"
            return

        indent = prefix + "{"
        for i, (key, val) in enumerate(items):
            if not self._task_info_in_repr and key.startswith("task_"):
                continue

            if i == len(self.keys()) - 1:
                end = "}"
            else:
                end = ","
            key_str = "'" + key + "'" + ": "
            val_str = pprint.pformat(val)
            if len(prefix) + len(key_str) + len(val_str) < 80:
                yield indent + key_str + val_str + end
            else:
                yield indent + key_str
                indent = prefix + "   "
                for l in val_str.split("\n"):
                    yield indent + l if l.endswith(",") else indent + l + end
            indent = prefix + " "

    def __repr__(self, _repr_running={}, prefix=""):
        call_key = id(self), _get_ident()
        if _repr_running is None:
            _repr_running = {}
        if call_key in _repr_running:
            return "..."
        _repr_running[call_key] = 1
        try:
            if self is None:
                return "%s()" % (self.__class__.__name__,)
            return "\n".join(self._repr_gen(prefix))
        finally:
            del _repr_running[call_key]

    def _get_index_length(self, index_var="auto"):
        """Find the length of the index_var variable or look for a
        time dimension in the data set if index_var="auto"
        """
        if index_var == "auto":
            timevars = [var for var in self if var.endswith("Output.Abscissa.t")]
            if len(timevars) > 1:
                raise ValueError(
                    f"Multiple time variables found. Use 'index_var' argument to indicate which to use."
                )
            if len(timevars) == 0:
                raise ValueError(
                    "No time variable found. Use 'index_var' argument to indicate what variable should be used."
                )
            index_var = timevars[0]

        if index_var is not None:
            if index_var not in self:
                raise ValueError(
                    f"The index var {index_var} could not be found in the data "
                )
            index_data = np.array(self[index_var])
            if index_data.ndim != 1:
                raise ValueError(f"The index var {index_var} should be a 1D array")

            index_len = index_data.shape[0]
        else:
            index_len = 1
        return index_len

    def to_dataframe(
        self,
        index_var: Optional[str] = "auto",
        interp_var=None,
        interp_val=None,
        interp_method="cubic",
    ):
        """Convert the output to a pandas dataframe.

        Parameters:
        -----------
        index_var: str
            Name of the variable to use as axis 0 in the dataframe.
            If "auto" is given the system will look for variables ending with
            "Ouput.Abcsissa.t". If 'None' no index variable is used an only a single
            row is returned in the dataframe.
        interp_var: str
            Name of the variable on which the data is interpolating/resampled.
        interp_val: np.ndarray
            Values to use when re-interpolating/resampling the data.
        interp_method: str
            Method to use when re-interpolating/resampling the data. Defaults to 'cubic'.

        Returns:
        --------
        df: pandas.DataFrame
            Dataframe with the output data.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for this function")

        excluded_vars = ["task_macro"]

        var_list = set(self.keys()) - set(excluded_vars)

        index_len = self._get_index_length(index_var)

        dfs = []
        for var in var_list:
            data = self[var]
            if isinstance(data, (int, float, str)):
                data = np.array(data)
            if isinstance(data, np.ndarray):
                indices = np.array(list(np.ndindex(data.shape)))
                data = np.atleast_2d(data.T).T
                if data.shape[0] != index_len:
                    data = data.flatten()
                    data = np.repeat(data[np.newaxis, :], index_len, axis=0)
                else:
                    indices = np.array(list(np.ndindex(data.shape[1:])))

                if len(indices) == 1:
                    col_names = [var]
                else:
                    col_names = [
                        var + "".join(f"[{i}]" for i in index) for index in indices
                    ]
                dfs.append(pd.DataFrame(data, columns=col_names))

        dfout = pd.concat(dfs, axis=1).convert_dtypes(
            convert_integer=False, convert_floating=False
        )

        if interp_var is not None:
            if interp_var not in dfout.columns:
                raise ValueError(
                    f"The `interp_var` {interp_var} could not be found in the data"
                )
            if interp_val is None:
                interp_val = dfout[interp_var]
            time_columns = list(dfout.columns[dfout.apply(pd.Series.nunique) > 1])
            constant_columns = dfout.columns.difference(time_columns)
            if interp_var not in time_columns:
                raise ValueError("The `interp_var` should not be a constant")

            dfout = dfout.set_index(interp_var, drop=True)
            dfout = dfout.reindex(dfout.index.union(interp_val))
            dfout[time_columns] = dfout[time_columns].interpolate(interp_method)
            dfout[constant_columns] = dfout[constant_columns].fillna(method="bfill")

            dfout = dfout.loc[interp_val]
            dfout.reset_index(inplace=True)

        return dfout


def _recursive_replace(iterable, old, new):
    for i, elem in enumerate(iterable):
        if isinstance(elem, list):
            _recursive_replace(elem, old, new)
        elif elem == old:
            iterable[i] = new


TRIPEL_QUOTE_WRAP = re.compile(r'([^\[\]",\s]+)')


def _parse_data(val):
    """Convert a str AnyBody data repr into Numpy array."""
    if val.startswith("{") and val.endswith("}"):
        val = val.replace("{", "[").replace("}", "]")
    if val == "[...]":
        val = '"..."'
    try:
        out = literal_eval(val)
    except (SyntaxError, ValueError):
        try:
            if "nan," in val:
                # handle the case where AnyBody has output 'nan' values
                val2 = val.replace("nan,", ' "nan",')
                out = literal_eval(val2)
                recursive_replace(out, "nan", float("nan"))
            else:
                raise SyntaxError
        except (SyntaxError, ValueError):
            val, _ = TRIPEL_QUOTE_WRAP.subn(r"'''\1'''", val)
            if val == "":
                val = "None"
            if val.startswith('"') and val.endswith('"'):
                val = "'''" + val[1:-1] + r"'''"
            out = literal_eval(val)
    if isinstance(out, list):
        out = np.array(out)
    return out


ABOVE_NORMAL_PRIORITY_CLASS = 0x8000
BELOW_NORMAL_PRIORITY_CLASS = 0x4000
IDLE_PRIORITY_CLASS = 0x0040
NORMAL_PRIORITY_CLASS = 0x0020


NAME_PATTERN = re.compile(r"Main\.[\w\.]*")


def correct_dump_prefix(raw, idx):
    """Find the correct prefix to use in the output"""
    # The -1000 hack is to avoid coping large strings in memory,
    # since we really only need to access the previous line.
    dumpline = raw[max(0, idx - 1000) : idx].strip().rsplit("\n", 1)[-1]
    if dumpline.startswith("#### Macro command"):
        m = NAME_PATTERN.search(dumpline)
        if m:
            return m.group(0)


ERROR_PATTERN = re.compile(
    r"^((ERROR)|(Model loading skipped)).*$", flags=re.IGNORECASE | re.M
)
WARNING_PATTERN = re.compile(r"^(WARNING).*$", flags=re.IGNORECASE | re.M)
DUMP_PATTERN = re.compile(r"^(Main.*?)\s=\s(.*?(?:\n\s\s.*?)*);", flags=re.M)


def parse_anybodycon_output(
    raw, errors_to_ignore=None, warnings_to_include=None, fatal_warnings=False
):
    """Parse the output log file from AnyBodyConsole to
    for data, errors and warnings. If fatal_warnins is
    True, then warnings are also added to the error list.
    """
    warnings_to_include = warnings_to_include or []
    errors_to_ignore = errors_to_ignore or []
    output = AnyPyProcessOutput()
    # Find all data in logfile
    prefix_replacement = ("", "")
    for dump in DUMP_PATTERN.finditer(raw):
        name, val = dump.group(1), dump.group(2)
        new_prefix = correct_dump_prefix(raw, dump.start())
        if new_prefix:
            prefix_replacement = (name, new_prefix)
        name = name.replace(*prefix_replacement)
        try:
            val = _parse_data(dump.group(2))
        except (SyntaxError, ValueError):
            warnings.warn("\n\nCould not parse console output:\n" + name)
        output[name] = val
    error_list = []

    def _add_non_ignored_errors(error_line):
        for ignored_err in errors_to_ignore:
            if ignored_err in error_line:
                break
        else:
            error_list.append(error_line)

    # Find all errors in logfile
    for match in ERROR_PATTERN.finditer(raw):
        _add_non_ignored_errors(match.group(0))
    # Find all warnings in logfile
    warning_list = []
    for match in WARNING_PATTERN.finditer(raw):
        for case in warnings_to_include:
            if case in match.group(0):
                if fatal_warnings:
                    _add_non_ignored_errors(match.group(0))
                warning_list.append(match.group(0))
                break
    if error_list:
        output["ERROR"] = error_list
    if warning_list:
        output["WARNING"] = warning_list
    return output


def get_ncpu():
    """Return the number of CPUs in the computer."""
    from multiprocessing import cpu_count

    return cpu_count()


def silentremove(filename):
    """Remove a file ignoring cases where the file does not exits."""
    if not filename:
        return
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:  # errno.ENOENT : no such file or directory
            logging.debug(f"Error removing file: {filename}")
            raise  # re-raise exception if a different error occured


def make_hash(o):
    """Make a hash from a dictionary, list, tuple or set.

    Create the hash to any sublevel that contains
    only other hashable types (including any lists, tuples, sets, and
    dictionaries).
    http://stackoverflow.com/questions/5884066/hashing-a-python-dictionary
    """
    if isinstance(o, (set, tuple, list)):

        return hash(tuple([make_hash(e) for e in o]))

    elif not isinstance(o, dict):

        return hash(o)

    new_o = copy.deepcopy(o)
    for k, v in new_o.items():
        new_o[k] = make_hash(v)

    return hash(tuple(frozenset(sorted(new_o.items()))))


_BM_CONSTANTS_AMMR1 = {
    "ON": "1",
    "OFF": "0",
    "_MUSCLES_NONE_": "0",
    "_MUSCLES_SIMPLE_": "1",
    "_MUSCLES_3E_HILL_": "2",
    "_HAND_SIMPLE_": "0",
    "_HAND_DETAILED_": "1",
    "_LEG_MODEL_OFF_": '"OFF"',
    "_LEG_MODEL_Leg_": '"Leg"',
    "_LEG_MODEL_TLEM_": '"TLEM"',
    "_MORPH_NONE_": "0",
    "_MORPH_TRUNK_TO_LEG_": "1",
    "_MORPH_LEG_TO_TRUNK_": "2",
    "_PELVIS_DISPLAY_NONE_": "0",
    "_PELVIS_DISPLAY_LEGPELVIS_ONLY_": "1",
    "_PELVIS_DISPLAY_LEGANDTRUNKPELVIS_": "2",
    "_SCALING_CUSTOM_": "-1",
    "_SCALING_STANDARD_": "0",
    "_SCALING_UNIFORM_": "1",
    "_SCALING_LENGTHMASS_": "2",
    "_SCALING_LENGTHMASSFAT_": "3",
    "_SCALING_UNIFORM_EXTMEASUREMENTS_": "4",
    "_SCALING_LENGTHMASS_EXTMEASUREMENTS_": "5",
    "_SCALING_LENGTHMASSFAT_EXTMEASUREMENTS_": "6",
    "_SCALING_LENGTHMASSFAT_MULTIDOFS_": "7",
}

_BM_CONSTANTS = {
    "ON": "1",
    "OFF": "0",
    "_MUSCLES_NONE_": "0",
    "_MUSCLES_SIMPLE_": "1",
    "_MUSCLES_3E_HILL_": "2",
    "_LEG_MODEL_OFF_": "0",
    "_LEG_MODEL_TLEM_": "1",
    "_LEG_MODEL_TLEM1_": "1",
    "_LEG_MODEL_TLEM2_": "2",
    "_LEG_MODEL_Leg_": "3",
    "_LEG_MODEL_LEG_": "3",
    "_MORPH_NONE_": "0",
    "_MORPH_TRUNK_TO_LEG_": "1",
    "_MORPH_LEG_TO_TRUNK_": "2",
    "_PELVIS_DISPLAY_NONE_": "0",
    "_PELVIS_DISPLAY_LEGPELVIS_ONLY_": "1",
    "_PELVIS_DISPLAY_LEGANDTRUNKPELVIS_": "2",
    "_DISC_STIFFNESS_NONE_": "0",
    "_DISC_STIFFNESS_LINEAR_": "1",
    "_DISC_STIFFNESS_NONLINEAR_": "2",
    "_SCALING_CUSTOM_": "-1",
    "_SCALING_STANDARD_": "0",
    "_SCALING_UNIFORM_": "1",
    "_SCALING_LENGTHMASS_": "2",
    "_SCALING_LENGTHMASSFAT_": "3",
    "_SCALING_UNIFORM_EXTMEASUREMENTS_": "4",
    "_SCALING_LENGTHMASS_EXTMEASUREMENTS_": "5",
    "_SCALING_LENGTHMASSFAT_EXTMEASUREMENTS_": "6",
    "_SCALING_LENGTHMASSFAT_MULTIDOFS_": "7",
    "CONST_MUSCLES_NONE": "0",
    "CONST_MUSCLES_SIMPLE": "1",
    "CONST_MUSCLES_3E_HILL": "2",
    "CONST_HAND_SIMPLE": "0",
    "CONST_HAND_DETAILED": "1",
    "CONST_LEG_MODEL_OFF": "0",
    "CONST_LEG_MODEL_TLEM": "1",
    "CONST_LEG_MODEL_TLEM2": "2",
    "CONST_LEG_MODEL_Leg": "3",
    "CONST_MORPH_NONE": "0",
    "CONST_MORPH_TRUNK_TO_LEG": "1",
    "CONST_MORPH_LEG_TO_TRUNK": "2",
    "CONST_PELVIS_DISPLAY_NONE": "0",
    "CONST_PELVIS_DISPLAY_LEGPELVIS_ONLY": "1",
    "CONST_PELVIS_DISPLAY_LEGANDTRUNKPELVIS": "2",
    "CONST_DISC_STIFFNESS_NONE": "0",
    "CONST_DISC_STIFFNESS_LINEAR": "1",
    "CONST_DISC_STIFFNESS_NONLINEAR ": "2",
    "CONST_SCALING_CUSTOM": "-1",
    "CONST_SCALING_STANDARD": "0",
    "CONST_SCALING_UNIFORM": "1",
    "CONST_SCALING_LENGTHMASS": "2",
    "CONST_SCALING_LENGTHMASSFAT": "3",
    "CONST_SCALING_UNIFORM_EXTMEASUREMENTS": "4",
    "CONST_SCALING_LENGTHMASS_EXTMEASUREMENTS": "5",
    "CONST_SCALING_LENGTHMASSFAT_EXTMEASUREMENTS": "6",
    "CONST_SCALING_LENGTHMASSFAT_MULTIDOFS": "7",
}


def get_bm_constants(ammr_path=None, ammr_version=2):
    """Return the BM_CONSTANT mapping.

    It will try to locate the mapping in the AMMR:
    Body/AAUHuman/Documentation/bm_constants.py

    If that fails it will use the ammr_version
    specification to select a value.
    """
    bm_constants = None
    if ammr_path is not None:
        filename = os.path.join(
            ammr_path, "Body/AAUHuman/Documentation/bm_constants.py"
        )
        try:
            with open(filename) as fh:
                bm_constants = literal_eval(fh.read())
        except IOError:
            pass
    if not isinstance(bm_constants, dict):
        bm_constants = _BM_CONSTANTS if ammr_version >= 2 else _BM_CONSTANTS_AMMR1
    return bm_constants


def replace_bm_constants(d, bm_constants=None):
    """Replace BM constants with value represenation."""
    if not bm_constants:
        bm_constants = _BM_CONSTANTS

    for k, v in d.items():
        if v in bm_constants:
            d[k] = bm_constants[v]
    return d
