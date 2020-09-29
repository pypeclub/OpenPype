@echo off

set __app__="Houdini 16.0"
set __exe__="C:\Program Files\Side Effects Software\Houdini 16.0.621\bin\houdini.exe"
if not exist %__exe__% goto :missing_app

start %__app__% %__exe__% %*

goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
