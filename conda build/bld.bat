xcopy "%RECIPE_DIR%"\..\src . /S/Y/I
cd src
"%PYTHON%" setup.py install
