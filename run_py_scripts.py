from pathlib import Path
import subprocess
import os


def run_script(f: Path):
    subprocess.run([f"python {str(f)}"], shell=True)


cwd = Path.cwd()
py_scripts = cwd.rglob("figures.py")
for f in py_scripts:
    os.chdir(f.parent)
    print(f)
    run_script(f)
    os.chdir(cwd)
