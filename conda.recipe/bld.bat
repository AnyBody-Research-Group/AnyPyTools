"%PYTHON%" setup.py install 

cd "%PREFIX%"
mkdir AnyPyToolsTutorial
cd AnyPyToolsTutorial
xcopy "%SRC_DIR%\Tutorial" . /S/Y/I

copy "%RECIPE_DIR%\AnyPyToolsTutorial.bat" "%SCRIPTS%\AnyPyToolsTutorial.bat"
REM cd "%PREFIX%"
REM mkdir Menu
REM  copy "%RECIPE_DIR%\menu-windows-manual.json" "%PREFIX%\Menu\AnyPyToolsTutorial.json"
REM copy "%SRC_DIR%\anypytools.ico" "%SCRIPTS%\anypytools.ico"
REM cd "%SRC_DIR%"
