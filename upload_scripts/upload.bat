#@echo off
setlocal

:loop
rem Define list of directories and types (format: "path;type")
set "dirs="C:\temp\laserball_tdfs;laserball" "C:\temp\sm5_tdfs;sm5""
set "upload_url="https://laserforce.spoo.uk/util/upload_tdf""

for %%d in (%dirs%) do (
    for /f "tokens=1,2 delims=;" %%a in ("%%~d") do (
        call :process_dir "%%a" "%%b"
    )
)

timeout /t 60 > NUL
goto loop

:process_dir
set "dir_path=%~1"
set "type=%~2"
set "uploaded_path=%dir_path%\uploaded"

if not exist "%uploaded_path%" mkdir "%uploaded_path%"

rem Iterate over files in the directory
for %%f in ("%dir_path%\*") do (
    echo Uploading "%%~nxf"...

    curl -f -F "upload_file=@%%~f" -F "type=%type%" %upload_url%

    if errorlevel 1 (
        echo Error: Curl call failed for %%~nxf
        timeout /t 10
        exit
    )

    move /Y "%%~f" "%uploaded_path%" >nul
)

rem Delete files older than 7 days in uploaded folder
forfiles /p "%uploaded_path%" /m * /d -7 /c "cmd /c del @path" 2>nul

exit /b