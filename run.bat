@echo off
REM md-forge launcher (Windows). First run installs deps, later runs are offline.
pip install -r requirements.txt
python md_forge.py
