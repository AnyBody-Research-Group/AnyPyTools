#!/bin/bash
$PYTHON setup.py install

cd ${PREFIX}
mkdir AnyPyToolsTutorial
cp -R ${SRC_DIR}/Tutorial/* ${PREFIX}/AnyPyToolsTutorial/
#cp ${RECIPE_DIR}/AnyPyToolsTutorial.bat ${SCRIPTS}/AnyPyToolsTutorial.bat
#cp ${RECIPE_DIR}/AnyPyToolsTutorial.bat ${PREFIX}/bin/AnyPyToolsTutorial.bat
