from anypytools import AnyPyProcess
from anypytools.macro_commands import Load, RunOperation

app = AnyPyProcess(num_processes=3)

macro = [Load("main.any"), RunOperation("Main.Study.InverseDynamics")]

app.start_macro(macro, search_subdirs="model[1-9].*main.any")
