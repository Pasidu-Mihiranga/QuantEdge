# Windows equivalent of the Makefile. Usage: .\make.ps1 <target>
param([Parameter(Position = 0)][string]$Target = "help",
      [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

function Setup {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv venv --allow-existing --python 3.12 .venv
        uv pip install --python $py -r requirements.txt -e .
    } else {
        py -3.12 -m venv .venv
        & $py -m pip install -q -r requirements.txt -e .
    }
}

switch ($Target) {
    "setup" { Setup }
    "data"     { & $py -m quantedge.data.download --refresh }
    "pipeline" { & $py -m quantedge.pipeline @Rest }
    "run"      { if (-not (Test-Path $py)) { Setup }; & $py -m streamlit run app/Home.py }
    "pdf"      { & $py scripts/build_pdfs.py }
    "test"     { & $py -m pytest -m "not slow and not network" }
    "test-all" { & $py -m pytest }
    "lint"     { & $py -m ruff check src tests app scripts }
    "defence" {
        & $py scripts/run_notebooks.py
        & $py scripts/build_defence_pack.py
    }
    "notebooks" {
        & $py -m pip install -q -r requirements-notebooks.txt
        & $py scripts/run_notebooks.py @Rest
    }
    default    { "Targets: setup, data, pipeline, run, test, test-all, lint, notebooks, defence, pdf" }
}
