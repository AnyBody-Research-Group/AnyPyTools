from anypytools.abcutils import AnyPyProcess

nSteplist = [10, 20, 40, 50, 60, 70, 80, 90, 100, 110, 120]
app = AnyPyProcess(num_processes=2)

macrolist = []
for nStep in nSteplist:
    macrolist.append(
        [
            'load "Demo.Arm2D.any" -def N_STEP="{0}"'.format(nStep),
            "operation Main.Study.InverseDynamics",
            "run",
        ]
    )

app.start_macro(macrolist)
