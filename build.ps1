$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment' }
}
& .venv\Scripts\python.exe -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Could not install build requirements' }
& .venv\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name TokenPricer --add-data 'prices.json;.' app.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Write-Output 'Ready: dist\TokenPricer.exe'
