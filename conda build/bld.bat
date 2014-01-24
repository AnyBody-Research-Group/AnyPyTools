mkdir src
cd src
xcopy "%RECIPE_DIR%"\..\src . /S/Y/I
cd ..
xcopy "%RECIPE_DIR%"\..\setup.py . /S/Y/I

"%PYTHON%" setup.py install

cd "%PREFIX%"
mkdir AnyPyToolsTutorial
cd AnyPyToolsTutorial
xcopy "%RECIPE_DIR%\..\Tutorial\AnyPyTools_Tutorial.ipynb" . /S/Y/I
xcopy "%RECIPE_DIR%\..\Tutorial\Knee.any" . /S/Y/I
mkdir BatchProcessExample
cd BatchProcessExample
xcopy "%RECIPE_DIR%\..\Tutorial\BatchProcessExample" . /S/Y/I

cd "%PREFIX%"
mkdir Menu
copy "%RECIPE_DIR%\menu-windows_manual.json" "%PREFIX%\Menu\AnyPyToolsTutorial.json"
copy "%RECIPE_DIR%\..\anypytools.ico" "%PREFIX%\Menu\anypytools.ico"