# Windows equivalent of the Makefile. Usage: .\make.ps1 <target>
param([Parameter(Position = 0)][string]$Target = "help",
      [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

switch ($Target) {
    "setup" {
        uv venv --python 3.12 .venv
        uv pip install --python $py -r requirements.txt
        uv pip install --python $py -e .
    }
    "data"     { & $py -m quantedge.data.download --refresh }
    "pipeline" { & $py -m quantedge.pipeline @Rest }
    "run"      { & $py -m streamlit run app/Home.py }
    "test"     { & $py -m pytest -m "not slow and not network" }
    "test-all" { & $py -m pytest }
    "lint"     { & $py -m ruff check src tests app scripts }
    default    { "Targets: setup, data, pipeline, run, test, test-all, lint" }
}
