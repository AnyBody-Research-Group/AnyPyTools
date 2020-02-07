from anypytools.abcutils import AnyPyProcess

app = AnyPyProcess(num_processes=3)

macrolist = [['load "main.any"', "operation Main.Study.InverseDynamics", "run", "exit"]]

app.start_macro(macrolist, search_subdirs="[model[1-9].*main.any")
