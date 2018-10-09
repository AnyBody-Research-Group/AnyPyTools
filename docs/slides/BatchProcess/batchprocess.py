from anypytools import AnyPyProcess
from anypytools.macro_commands import Load, OperationRun

app = AnyPyProcess(num_processes=3)

macro = [Load("main.any"), OperationRun("Main.Study.InverseDynamics")]

app.start_macro(macro, search_subdirs="model[1-9].*main.any")
