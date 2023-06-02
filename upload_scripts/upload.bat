:loop
for %%i in (C:\laserball_tdfs\*) do (
    curl -F "upload_file=@%%i" -F "type=laserball" https://laserforce.spoo.uk/util/upload_tdf
    del %%i
)
for %%i in (C:\sm5_tdfs\*) do (
    curl -F "upload_file=@%%i" -F "type=sm5" https://laserforce.spoo.uk/util/upload_tdf
    del "%%i"
)
timeout /t 60 > NUL
goto loop