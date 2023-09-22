from pathlib import Path
import subprocess
import os
import re


def run_script(f: Path):
    subprocess.run([f"python {str(f)}"], shell=True)


# Get modified or added files from the last git commit
result = subprocess.run(
    ["git", "diff", "--name-only", "HEAD^", "HEAD"], stdout=subprocess.PIPE
)
print(result.stdout.decode("utf-8"))
files = re.split("\n|\t", result.stdout.decode("utf-8"))[:-1]

# Find parent (top level) directories for each of the files
script_dirs = []
for f in files:
    # if Path(f).exists() and len(f) > 1:
    script_dirs.append(Path(f).parts[0])
script_dirs = set(script_dirs)
print(script_dirs)

# Run scripts in the parent directory of the modified files
cwd = Path.cwd()
for f in script_dirs:
    scripts = (cwd / f).glob("figures.py")
    for s in scripts:
        os.chdir(s.parent)
        print(s)
        run_script(s)
        os.chdir(cwd)
