# PyTest plugin.

Pytest is a fantastic test framework for Python code. AnyPyTools provides a
pytest plugin for running and testing AnyBody models. The plugin make pytest
collect and run AnyScript files with a `test_` prefix (e.g.
`test_mymodel.any`). Once loaded the plugin will attempt to execute a
`Main.RunTest` operation if it exists. If the models produce error while
loading and running, the framework considers it a failed test.

```{eval-rst}
.. automodule:: anypytools.pytest_plugin
    :members:
    :noindex:
```
