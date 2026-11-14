@echo off
rem Convergence study renders. Run this from the experiments folder.
set EXE=..\x64\Release\BuildingMyFirstRenderer.exe
if not exist data mkdir data

rem Reference: 4096 samples, seed 1000 (a seed no trial uses)
echo Rendering reference...
%EXE% 4096 1000 data\reference.bin > nul

rem Trials: 5 sample counts x 5 seeds
for %%N in (1 4 16 64 256) do (
    for %%S in (1 2 3 4 5) do (
        echo Rendering N=%%N seed=%%S
        %EXE% %%N %%S data\n%%N_s%%S.bin > nul
    )
)
echo All done.