mkdir src
cd src
xcopy "%RECIPE_DIR%"\..\src . /S/Y/I
cd ..
xcopy "%RECIPE_DIR%"\..\setup.py . /S/Y/I

"%PYTHON%" setup.py install
