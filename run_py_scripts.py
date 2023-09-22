from pathlib import Path
import subprocess
import os
import re
from joblib import Parallel, delayed

CWD = Path.cwd()


def run_script(f: Path):
    subprocess.run([f"python {str(f)}"], shell=True)


def run_scripts_in_dir(f: Path):
    scripts = (CWD / f).glob("figures.py")
    for s in scripts:
        os.chdir(s.parent)
        print(s)
        run_script(s)
        os.chdir(CWD)


def git_changed_files():
    """
    Retrieves the names of files that have been modified or added in the last git commit.

    Returns:
    - A list of file names that have been modified or added in the last git commit.
    """
    output = subprocess.check_output(["git", "diff", "--name-only", "HEAD", "HEAD~1"])
    files = output.decode().splitlines()
    files = [f.rstrip() for f in files]
    return files


def main():
    # Get modified or added files from the last git commit
    files = git_changed_files()

    # Find parent (top level) directories for each of the files
    script_dirs = []
    for f in files:
        # if Path(f).exists() and len(f) > 1:
        script_dirs.append(Path(f).parts[0])
    script_dirs = set(script_dirs)
    print(script_dirs)

    # Run scripts in the parent directory of the modified files
    Parallel(n_jobs=-1)(delayed(run_scripts_in_dir)(f) for f in script_dirs)


if __name__ == "__main__":
    main()
