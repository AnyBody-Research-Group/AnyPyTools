# -*- coding: utf-8 -*-
# pylint: disable: line-too-long
"""
Created on Mon Mar 23 21:14:59 2015.

@author: Morten
"""
import types
import logging
from pprint import pprint, pformat  # noqa
from copy import deepcopy
from collections.abc import MutableSequence

import numpy as np
from scipy.stats import distributions

from anypytools.tools import define2str, path2str, array2anyscript

logger = logging.getLogger("abt.anypytools")


__all__ = [
    "MacroCommand",
    "Load",
    "SetValue",
    "SetValue_random",
    "Dump",
    "SaveDesign",
    "LoadDesign",
    "SaveValues",
    "LoadValues",
    "UpdateValues",
    "OperationRun",
    "SaveData",
]


def _isgenerator(x):
    return isinstance(x, types.GeneratorType)


def _batch(iterable, n=1):
    length = len(iterable)
    for ndx in range(0, length, n):
        yield iterable[ndx : min(ndx + n, length)]


class MacroCommand(object):
    """Class for custom macro commands.

    This class also serves as base class for other macro commands.

    Examples
    --------
    >>> mc = MacroCommand('operation "Main.MyStudy.InverseDynamics"') )
    >>> print(mc)
    operation "Main.MyStudy.InverseDynamics"

    """

    def __init__(self, command):
        if not isinstance(command, list):
            self.cmd = [command]
        else:
            self.cmd = command

    def __repr__(self):
        return self.get_macro(0)

    def get_macro(self, index, **kwarg):
        """Create a string representation of the macro.

        Parameters
        ----------
        index : int
            The index for the macro beeing generated. Some child classes
            use the index to generate different macros depending on the
            index.

        Returns
        -------
        string
            A string with the AnyScript macro

        """
        return "\n".join(self.cmd)


class Load(MacroCommand):
    """Create a load macro command.

    Parameters
    ----------
    filename : str
        Path of the file to load
    defs : dict
        Dictionary of defines statements to set during load
    paths : dict
        Dictionary of path staements to set during load

    Examples
    --------
    >>> Load('model.main.any')
    load "model.main.any"

    >>> paths = {'DATA':'c:/MyModel/Data'}
    >>> defines = {'EXCLUDE_ARMS':None, 'N_STEP':20}
    >>> Load('c:/MyModel/model.main.any', defines, paths)
    load "c:/MyModel/model.main.any" -def EXCLUDE_ARMS="" -def N_STEP="20" -p DATA=---"c:/MyModel/Data"

    >>> mcr = AnyMacro( Load('model_{id}.main.any'), counter_token = '{id}')
    >>> mcr.create_macros(3)
    [[u'load "model_0.main.any"'],
     [u'load "model_1.main.any"'],
     [u'load "model_2.main.any"']]

    """

    def __init__(self, filename, defs={}, paths={}):
        self.filename = filename
        self.defs = defs.copy()
        self.paths = paths.copy()

    def get_macro(self, index, **kwarg):
        cmd = ['load "{}"'.format(self.filename)]

        for key in sorted(self.defs):
            value = self.defs[key]
            cmd.append(define2str(key, value))
        for key in sorted(self.paths):
            value = self.paths[key]
            cmd.append(path2str(key, value))

        return " ".join(cmd)


class SetValue(MacroCommand):
    """Create 'Set Value' classoperation macro command.

    Parameters
    ----------
    var : string
        An AnyScript variable.
    value : number or list of number
        A value or list of values to assign to the AnyScript variable.

    Examples
    ---------
    Set a single values:

    >>> SetValue('Main.Study.myvar1', 23.1)
    classoperation Main.Study.myvar1 "Set Value" --value="23.1"

    >>> SetValue('Main.Study.myvar2', np.array([2,3,4]))
    classoperation Main.Study.myvar2 "Set Value" --value="{2,3,4}"

    Set variable across different macros

    >>> SetValue('Main.Study.myvar1',[1,2,3])
    classoperation Main.Study.myvar1 "Set Value" --value="1"
    classoperation Main.Study.myvar1 "Set Value" --value="2"
    classoperation Main.Study.myvar1 "Set Value" --value="3"

    Here is a elaborate example:

    >>> mg = AnyMacro( Load('MyModel.main.any'),
                     SetValue('Main.Study.myvar1',[1,2]),
                     OperationRun('Main.Study.InverseDynamics') )
    >>> mg.number_of_macros = 2
    [['load "MyModel.main.any"',
      'classoperation Main.Study.myvar1 "Set Value" --value="1"',
      'operation Main.Study.InverseDynamics',
      'run'],
     ['load "MyModel.main.any"',
      'classoperation Main.Study.myvar1 "Set Value" --value="2"',
      'operation Main.Study.InverseDynamics',
      'run']]

    If we generate more macros that there are values then the values are just
    repeated

    >>> mg.number_of_macros = 4
    >>> mg
    [['load "MyModel.main.any"',
      'classoperation Main.Study.myvar1 "Set Value" --value="1"',
      'operation Main.Study.InverseDynamics',
      'run'],
     ['load "MyModel.main.any"',
      'classoperation Main.Study.myvar1 "Set Value" --value="2"',
      'operation Main.Study.InverseDynamics',
      'run'],
     ['load "MyModel.main.any"',
      'classoperation Main.Study.myvar1 "Set Value" --value="1"',
      'operation Main.Study.InverseDynamics',
      'run'],
     ['load "MyModel.main.any"',
      'classoperation Main.Study.myvar1 "Set Value" --value="2"',
      'operation Main.Study.InverseDynamics',
      'run']]

    """

    def __init__(self, var, value):
        self.var = var
        self.value = value

    def __repr__(self):
        if isinstance(self.value, list):
            n_elem = len(self.value)
        else:
            n_elem = 1

        return "\n".join([self.get_macro(i) for i in range(n_elem)])

    def get_macro(self, index, **kwarg):
        if isinstance(self.value, list):
            val = self.value[index % len(self.value)]
        else:
            val = self.value
        return self._format_macro(val)

    def _format_macro(self, val):
        if isinstance(val, np.ndarray):
            val = array2anyscript(val)
        elif isinstance(val, float):
            val = "{:.12g}".format(val)
        elif isinstance(val, int):
            val = "{:d}".format(val)
        return 'classoperation {0} "Set Value" --value="{1}"'.format(self.var, val)


class SetValue_random(SetValue):
    """Create a 'Set Value' macro command from a distribution.

    The value is connected to a distibution in scipy.stats.distributions.

    Parameters
    ----------
    var : str
        An AnyScript variable.
    frozen_distribution : <scipy.stats.distributions.rv_frozen>
        A frozen distribution from scipy.stats.distributions
    default_lower_tail_probability : float
        The lower tail probability of the default value. Defaults to 0.5 which
        is the mean value.


    Examples
    --------
    Creating normal macros will use the default values. Usually the 50 percentile
    (mean values).

    >>> np.random.seed(1)
    >>> from scipy.stats.distributions import logistic, norm
    >>> log_dist = logistic( loc= [1,3,4],scale = [0.1,0.5,1] )
    >>> norm_dist = norm( loc= [0,0,0],scale = [0.1,0.5,1] )
    >>> cmd = [SetValue_random('Main.MyVar1', log_dist), SetValue_random('Main.MyVar2', norm_dist) ]
    >>> mg = AnyMacro(cmd, number_of_macros = 3)
    >>> mg
    [['classoperation Main.MyVar1 "Set Value" --value="{0,0,0}"',
      'classoperation Main.MyVar2 "Set Value" --value="{1,3,4}"'],
     ['classoperation Main.MyVar1 "Set Value" --value="{0,0,0}"',
      'classoperation Main.MyVar2 "Set Value" --value="{1,3,4}"'],
     ['classoperation Main.MyVar1 "Set Value" --value="{0,0,0}"',
      'classoperation Main.MyVar2 "Set Value" --value="{1,3,4}"']]

    Values can be sampled randomly in a 'Monte Carlo' fashion. Note that the
    first value is still the defaut mean values

    >>> mg.create_macros_MonteCarlo()
    [['classoperation Main.MyVar1 "Set Value" --value="{0,0,0}"',
      'classoperation Main.MyVar2 "Set Value" --value="{1,3,4}"'],
     ['classoperation Main.MyVar1 "Set Value" --value="{-0.0209517840916,0.291902872134,-3.68494766954}"',
      'classoperation Main.MyVar2 "Set Value" --value="{0.916378512121,2.11986245798,1.71459079162}"'],
     ['classoperation Main.MyVar1 "Set Value" --value="{-0.0891762169545,-0.198666812922,-0.261723075945}"',
      'classoperation Main.MyVar2 "Set Value" --value="{1.01555799978,2.83695956934,4.7778636562}"']]

    Values can also be sampled with a Latin Hyper Cube sampler.

    >>> mg.create_macros_LHS()
    [['classoperation Main.MyVar1 "Set Value" --value="{0.0928967116493,-0.591418725401,-0.484696993931}"',
      'classoperation Main.MyVar2 "Set Value" --value="{1.01049414425,2.46211329129,5.73806916203}"'],
     ['classoperation Main.MyVar1 "Set Value" --value="{-0.0166741228961,0.707722119582,-0.294180629253}"',
      'classoperation Main.MyVar2 "Set Value" --value="{1.11326829265,2.66016732923,4.28054911097}"'],
     ['classoperation Main.MyVar1 "Set Value" --value="{-0.20265197275,0.114947152258,0.924796936287}"',
      'classoperation Main.MyVar2 "Set Value" --value="{0.806864877696,4.4114188826,2.93941843565}"']]

    """

    def __init__(self, var, frozen_distribution, default_lower_tail_probability=0.5):
        self.var = var
        if not isinstance(frozen_distribution, distributions.rv_frozen):
            raise TypeError(
                "frozen_distribution must be frozen distribtuion from \
                            scipy.stats.distributions"
            )

        self.rv = frozen_distribution

        self.meanvalue = frozen_distribution.mean()
        if isinstance(self.meanvalue, np.ndarray):
            self.shape = self.meanvalue.shape
            self.n_factors = np.prod(self.shape)
            self.default_lower_tail_probability = (
                default_lower_tail_probability * np.ones(self.shape)
            )
        else:
            self.shape = None
            self.n_factors = 1
            self.default_lower_tail_probability = default_lower_tail_probability

    def __repr__(self):
        return self.get_macro(0)

    def get_macro(self, index, lower_tail_probability=None, **kwarg):
        if lower_tail_probability is None:
            lower_tail_probability = self.default_lower_tail_probability

        if self.shape is None and isinstance(lower_tail_probability, np.ndarray):
            lower_tail_probability = lower_tail_probability[0]

        val = self.rv.ppf(lower_tail_probability).reshape(self.shape)
        # Replace any nan from ppf function with actual sampled values.
        if np.any(np.isnan(val)):
            val[np.isnan(val)] = self.rv.rvs()[np.isnan(val)]

        return self._format_macro(val)


class Dump(MacroCommand):
    """Create a Dump classoperation macro command.

    Parameters
    ----------
    var : str or list of str
        The anyscript values to create a 'Dump' macro command for
    include_in_macro: int or list of int
        Specifices in which macros [0,1,2....NumberOfMacros] to include the
        dump command.
        If None, the command is included in all macros.

    Examples
    ---------
    >>> Dump('Main.Study.myvar1')
    classoperation Main.Study.myvar1 "Dump"

    Only include the dump command in the two first macro

    >>> mg = AnyMacro(number_of_macros = 5)
    >>> mg.append(Load('mymodel.main.any'))
    >>> mg.append(Dump('Main.Study.myvar1', include_in_macro = [0,1]))
    >>> mg
    [['load "mymodel.main.any"', 'classoperation Main.Study.myvar1 "Dump"'],
     ['load "mymodel.main.any"', 'classoperation Main.Study.myvar1 "Dump"'],
     ['load "mymodel.main.any"'],
     ['load "mymodel.main.any"'],
     ['load "mymodel.main.any"']]

    """

    def __init__(self, var, include_in_macro=None):
        if not isinstance(var, list):
            self.var_list = [var]
        else:
            self.var_list = var
        self._include_in_macro = include_in_macro

    def get_macro(self, index, **kwarg):
        cmd = []
        if self._include_in_macro is None or index in self._include_in_macro:
            for var in self.var_list:
                cmd.append('classoperation {0} "Dump"'.format(var))
        return "\n".join(cmd)


class SaveDesign(MacroCommand):
    """Create a Save Design classoperation macro command.

    Parameters
    ----------
    operation : str
        The AnyScript operation
    filename : str
        The filename in which to save the design

    Examples
    --------
    >>> SaveDesign('Main.MyStudy.Kinematics', 'c:/design.txt')
    classoperation Main.MyStudy.Kinematics "Save design" --file="c:/design.txt"

    """

    def __init__(self, operation, filename):
        self.filename = filename
        self.operation = operation

    def get_macro(self, index, **kwarg):
        return 'classoperation {} "Save design" --file="{}"'.format(
            self.operation, self.filename
        )


class LoadDesign(MacroCommand):
    """Create a Load Design classoperation macro command.

    Parameters
    ----------
    operation : str
        The AnyScript operation
    filename : str
        The file in which to load the design from

    Examples
    --------
    >>> LoadDesign('Main.MyStudy.Kinematics', 'c:/design.txt')
    classoperation Main.MyStudy.Kinematics "Load design" --file="c:/design.txt"

    """

    def __init__(self, operation, filename):
        self.filename = filename
        self.operation = operation

    def get_macro(self, index, **kwarg):
        return 'classoperation {} "Load design" --file="{}"'.format(
            self.operation, self.filename
        )


class SaveValues(MacroCommand):
    """Create a Save Values classoperation macro command.

    Parameters
    ----------
    filename : str
        The anyset file to save the values to

    Examples
    --------
    >>> SaveValues('c:/values.anyset')
    classoperation Main "Save Values" --file="c:/values.anyset"

    """

    def __init__(self, filename):
        self.filename = filename

    def get_macro(self, index, **kwarg):
        return 'classoperation Main "Save Values" --file="{}"'.format(self.filename)


class SaveData(MacroCommand):
    """Create a Save Data classoperation macro command.

    This macro operation will save all data from a study to a
    HDF5 file.

    Parameters
    ----------
    operation : str
        Operation to save the h5 from
    filename : str
        The anyset file to save the values to

    Examples
    --------
    >>> SaveData('Main.Study', 'output.anydata.h5')
    classoperation Main.Study.Output "Save data" --type="Deep" --file="output.anydata.h5"

    """

    def __init__(self, operation, filename):
        self.filename = filename
        self.opeation = operation

    def get_macro(self, index, **kwarg):
        macro_str = 'classoperation {}.Output "Save data" --type="Deep" --file="{}"'
        return macro_str.format(self.opeation, self.filename)


class LoadValues(MacroCommand):
    """Create a Load Values classoperation macro command.

    Parameters
    ----------
    filename : str
        The anyset file to load the values from.

    Examples
    --------
    >>> LoadValues('c:/values.anyset')
    classoperation Main "Load Values" --file="c:/values.anyset"

    """

    def __init__(self, filename):
        self.filename = filename

    def get_macro(self, index, **kwarg):
        return 'classoperation Main "Load Values" --file="{}"'.format(self.filename)


class UpdateValues(MacroCommand):
    """Create an 'Update Values' classoperation macro command.

    Examples
    --------
    >>> UpdateValues()
    classoperation Main "Update Values"

    """

    def __init__(self):
        pass

    def get_macro(self, index, **kwarg):
        return 'classoperation Main "Update Values"'


class OperationRun(MacroCommand):
    """Create a macro command to select and run an operation.

    Examples
    --------
    >>> OperationRun('Main.MyStudy.Kinematics')
    >>> pprint( mg.generate_macros())
    operation Main.MyStudy.Kinematics
    run

    >>> mg = AnyMacro(Load('my_model.main.any'),
                   OperationRun('Main.MyStudy.Kinematics'))
    >>> mg.create_macros()
    [[u'load "my_model.main.any"', u'operation Main.MyStudy.Kinematics', u'run']]

    """

    def __init__(self, operation):
        self.operation = operation

    def get_macro(self, index, **kwarg):
        return "operation {}".format(self.operation) + "\n" + "run"


class AnyMacro(MutableSequence):
    """
    Class to generate multiple macros.

    Use the class to contruct multiple anyscript macros from a single macro.
    E.g. for parameter studies, Monte Carlo, Latin Hyper Cube studies.

    Parameters
    ----------
    maco_commands : list or positional arguments
        A list of macro command classes. These may also be given a arbitrary number
        of positional arguments.
    counter_token : str
        A string in the macro commands which will be replace with a counter
        for every macro generated
    number_of_macros : int
        The default number of macros which are created. This can be overruled when
        calling the AnyMacro.create_macros() function. Defults to 1.
    seed : int or array_like
        A constant seed value used which will be used every time macros are created.
        Must be convertable to 32 bit unsigned integers.

    Returns
    -------
    An AnyMacro instance
        A Macro object for constructing the macro.


    Examples
    --------
    >>> mg = AnyMacro(number_of_macros = 22)
    >>> mg.append( Load('c:/MyModel/model.main.any', defs = {}, paths = {} ) )
    >>> mg.append( SetValue('Main.myvar', 12.3)  )
    >>> mg.extend( [RunOperation('Main.Study.Kinematics'),
                     Dump('Main.Study.Output.MyVar') ] )
    >>> mg
    [['load "c:/MyModel/model.main.any"',
      'classoperation Main.myvar "Set Value" --value="12.3"',
      'operation Main.Study.Kinematics',
      'run',
      'classoperation Main.Study.Output.MyVar "Dump"'],
     ['load "c:/MyModel/model.main.any"',
      'classoperation Main.myvar "Set Value" --value="12.3"',
      'operation Main.Study.Kinematics',
      'run',
      'classoperation Main.Study.Output.MyVar "Dump"']]


    >>> mg = AnyMacro( number_of_macros = 3, counter_token='{COUNTER}' )
    >>> mg.append(Load('c:/MyModel/model_{COUNTER}_.main.any') )
    >>> pprint(mg.create_macros())
    [['load "c:/MyModel/model_0_.main.any"'],
     ['load "c:/MyModel/model_1_.main.any"'],
     ['load "c:/MyModel/model_2_.main.any"']]



    """

    def __init__(self, *args, **kwargs):  # number_of_macros=1, counter_token = None ):
        super(AnyMacro, self).__init__()
        if len(args) == 0:
            self._list = list()
        else:
            if len(args) == 1 and isinstance(args[0], list):
                args = args[0]
            for arg in args:
                if not isinstance(arg, MacroCommand):
                    raise ValueError("Argument must be valid macro command classes")
            self._list = list(args)

        self.seed = kwargs.pop("seed", None)

        self.number_of_macros = kwargs.pop("number_of_macros", 1)
        self.counter_token = kwargs.pop("counter_token", None)

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise NotImplementedError("operator must be integer")
        mg = deepcopy(self)
        mg.number_of_macros = mg.number_of_macros * round(other)
        return mg

    __rmul__ = __mul__

    def __len__(self):
        return len(self._list)

    def __getitem__(self, ii):
        return self._list[ii]

    def __delitem__(self, ii):
        del self._list[ii]

    def __setitem__(self, ii, val):
        self._list[ii] = val
        return self._list[ii]

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return pformat(self.create_macros())

    def insert(self, ii, val):
        self._list.insert(ii, val)

    def append(self, val):
        list_idx = len(self._list)
        self.insert(list_idx, val)

    def create_macros(self, number_of_macros=None, batch_size=None):
        """Generate a given number of macros.

        The function return its output either as list (batch_size = None) or in batches
        as generator object (memory efficient when generating many macros)

        Parameters
        ----------
        number_of_macros : int (Optional)
            The number of macro to create.
        batch_size : int (Optional)
            If specified the function will return a generator which creates macros in
            batches.

        Returns
        -------
        list or generator
            A list macros or a generator which creates macros in batches

        Examples
        --------
        >>> from anypytools import AnyMacro
        >>> from anypytools.macro_commands import *
        >>> macro = [
        ...     Load('c:/Model.main.any'),
        ...     OperationRun('Main.study.Kinematics'),
        ... ]
        >>> mg = AnyMacro(macro, number_of_macros=4)
        >>> macrolist = mg.create_macros()
        >>> pprint(macrolist)
        [['load "c:/Model.main.any"', 'operation Main.study.Kinematics', 'run'],
         ['load "c:/Model.main.any"', 'operation Main.study.Kinematics', 'run'],
         ['load "c:/Model.main.any"', 'operation Main.study.Kinematics', 'run'],
         ['load "c:/Model.main.any"', 'operation Main.study.Kinematics', 'run']]


        Generate macros in batches

        >>> mg = AnyMacro([Load('c:/Model.main.any')], number_of_macros = 6)
        >>> macro_gen =  mg.create_macros(batch_size=2)
        >>> for i, macros in enumerate( macro_gen ):
        ...     print('Batch ', i)
        ...     pprint(macros)
        Batch 0
        [['load "c:/Model.main.any"'], ['load "c:/Model.main.any"']]
        Batch 1
        [['load "c:/Model.main.any"'], ['load "c:/Model.main.any"']]
        Batch 2
        [['load "c:/Model.main.any"'], ['load "c:/Model.main.any"']]

        """
        if batch_size is not None:
            return _batch(self.create_macros(number_of_macros), n=batch_size)

        if number_of_macros is None:
            number_of_macros = self.number_of_macros
        if self.seed is not None:
            np.random.seed(self.seed)
        macro_list = []
        for macro_idx in range(number_of_macros):
            macro = []
            for elem in self:
                mcr = elem.get_macro(macro_idx)
                if self.counter_token:
                    mcr = mcr.replace(self.counter_token, str(macro_idx))
                if mcr != "":
                    macro.extend(mcr.split("\n"))
            macro_list.append(macro)
        return macro_list

    def create_macros_MonteCarlo(self, number_of_macros=None, batch_size=None):  # noqa
        """Generate AnyScript macros for monte carlos studies.

        The function returns macros for Monte Carlo parameter studies. This methods
        extends the `create_macros` methods with functionality to randomly vary
        parameters across macros.

        Values added with `SetValue_random` class are sampled randomly in a
        'Monte Carlo' fashion. Note that the values of the first macro
        is the defaut mean value.

        Parameters
        ----------
        number_of_macros : int (Optional)
            The number of macro to create.
        batch_size : int (Optional)
            If specified the function will return a generator which creates macros in
            batches.

        Returns
        -------
        list or generator
            A list macros or a generator which creates macros in batches

        Examples
        --------
        >>> np.random.seed(1)
        >>> from scipy.stats.distributions import logistic, norm
        >>> log_dist = logistic( loc= [1,3,4],scale = [0.1,0.5,1] )
        >>> norm_dist = norm( loc= [0,0,0],scale = [0.1,0.5,1] )
        >>> cmd = [SetValue_random('Main.MyVar1', log_dist), SetValue_random('Main.MyVar2', norm_dist) ]
        >>> mg = AnyMacro(cmd, number_of_macros = 3)
        >>> mg.create_macros_MonteCarlo()
        [['classoperation Main.MyVar1 "Set Value" --value="{0,0,0}"',
        'classoperation Main.MyVar2 "Set Value" --value="{1,3,4}"'],
        ['classoperation Main.MyVar1 "Set Value" --value="{-0.0209517840916,0.291902872134,-3.68494766954}"',
        'classoperation Main.MyVar2 "Set Value" --value="{0.916378512121,2.11986245798,1.71459079162}"'],
        ['classoperation Main.MyVar1 "Set Value" --value="{-0.0891762169545,-0.198666812922,-0.261723075945}"',
        'classoperation Main.MyVar2 "Set Value" --value="{1.01555799978,2.83695956934,4.7778636562}"']]

        """
        if batch_size is not None:
            return _batch(self.create_macros_MonteCarlo(number_of_macros), batch_size)

        if number_of_macros is None:
            number_of_macros = self.number_of_macros

        if self.seed is not None:
            np.random.seed(self.seed)

        macro_list = []
        for macro_idx in range(number_of_macros):
            macro = []
            lhs_idx = 0
            for elem in self:
                if isinstance(elem, SetValue_random):
                    if macro_idx == 0:
                        lower_tail_probability = (
                            None  # First macro get the default values
                        )
                    else:
                        lower_tail_probability = np.random.random(elem.n_factors)
                    mcr = elem.get_macro(macro_idx, lower_tail_probability)
                    lhs_idx += elem.n_factors
                else:
                    mcr = elem.get_macro(macro_idx)

                if self.counter_token:
                    mcr = mcr.replace(self.counter_token, str(macro_idx))
                if mcr != "":
                    macro.extend(mcr.split("\n"))
            macro_list.append(macro)
        return macro_list

    def create_macros_LHS(
        self,
        number_of_macros=None,
        criterion=None,  # noqa
        iterations=None,
        batch_size=None,
        append_default=False,
    ):
        """Generate AnyScript macros for Latin Hyper Cube Studies studies.

        Generates AnyScript macros for parameter studies using Latin hyper cube
        sampling. The macros added with the `SetValue_random` are created with
        with Latin Hypercube Sampling (LHS) of the parameter space. The number
        of generated macros determines the number of LHS samples.

        The method uses the pyDOE package to generate the LHS data.


        Parameters
        ----------
        number_of_macros : int (Optional)
            The number of macro to create.
        batch_size : int (Optional)
            If specified the function will return a generator which creates macros in
            batches.
        criterion : {None, 'c', 'm', 'cm', 'corr'}
            A a string that specifies how points are sampled
            (see: http://pythonhosted.org/pyDOE/randomized.html)
            `None` (Default) points are randomizes within the intervals.
            "center" or "c" center the points within the sampling intervals
            "maximin" or "m": maximize the minimum distance between points, but place
            the point in a randomized location within its interval
            "centermaximin" or "cm": same as “maximin”, but centered within the intervals
            "corr" minimize the maximum correlation coefficient
        iterations : int
            Specifies how many iterations are used to accomplished the selected criterion
        append_default : bool
            If True a macro with default (mean) values is appended to the returned list
            of returned macros


        Returns
        -------
        list or generator
            A list macros or a generator which creates macros in batches

        Examples
        --------
        >>> np.random.seed(1)
        >>> from scipy.stats.distributions import logistic, norm
        >>> log_dist = logistic( loc= [1,3,4],scale = [0.1,0.5,1] )
        >>> norm_dist = norm( loc= [0,0,0],scale = [0.1,0.5,1] )
        >>> cmd = [SetValue_random('Main.MyVar1', log_dist), SetValue_random('Main.MyVar2', norm_dist) ]
        >>> mg = AnyMacro(cmd, number_of_macros = 3)
        >>> mg.create_macros_LHS()
        [['classoperation Main.MyVar1 "Set Value" --value="{0.0928967116493,-0.591418725401,-0.484696993931}"',
        'classoperation Main.MyVar2 "Set Value" --value="{1.01049414425,2.46211329129,5.73806916203}"'],
        ['classoperation Main.MyVar1 "Set Value" --value="{-0.0166741228961,0.707722119582,-0.294180629253}"',
        'classoperation Main.MyVar2 "Set Value" --value="{1.11326829265,2.66016732923,4.28054911097}"'],
        ['classoperation Main.MyVar1 "Set Value" --value="{-0.20265197275,0.114947152258,0.924796936287}"',
        'classoperation Main.MyVar2 "Set Value" --value="{0.806864877696,4.4114188826,2.93941843565}"']]

        """  # noqa
        try:
            import pyDOE
        except ImportError:
            raise ImportError("The pyDOE package must be install to use this class")

        if batch_size is not None:
            return _batch(
                self.create_macros_LHS(number_of_macros, criterion, iterations),
                n=batch_size,
            )

        if number_of_macros is None:
            number_of_macros = self.number_of_macros

        if self.seed is not None:
            np.random.seed(self.seed)

        factors = sum([e.n_factors for e in self if isinstance(e, SetValue_random)])
        lhs_matrix = pyDOE.lhs(
            factors, number_of_macros, criterion=criterion, iterations=iterations
        )

        macro_list = []

        for macro_idx in range(number_of_macros):
            macro = []
            lhs_idx = 0
            for elem in self:
                if isinstance(elem, SetValue_random):
                    lhs_val = lhs_matrix[macro_idx, lhs_idx : lhs_idx + elem.n_factors]
                    mcr = elem.get_macro(macro_idx, lower_tail_probability=lhs_val)
                    lhs_idx += elem.n_factors
                else:
                    mcr = elem.get_macro(macro_idx)

                if self.counter_token:
                    mcr = mcr.replace(self.counter_token, str(macro_idx))
                if len(mcr) > 0:
                    macro.extend(mcr.split("\n"))
            macro_list.append(macro)
        if append_default:
            macro = []
            for elem in self:
                mcr = elem.get_macro(number_of_macros)
                if self.counter_token:
                    mcr = mcr.replace(self.counter_token, str(number_of_macros))
                if len(mcr) > 0:
                    macro.extend(mcr.split("\n"))
            macro_list.append(macro)
        return macro_list


if __name__ == "__main__":

    #    mg = PertubationMacroGenerator()
    #    mg.add_set_value_designvar('test',1)
    #    mg.add_set_value_designvar('test',2)
    #
    #    pprint(mg.generate_macros())
    #
    import pytest

    pytest.main(str("generate_macros.py --doctest-modules"))
