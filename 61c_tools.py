from datetime import datetime, timedelta
import argparse
import importlib
import os
import shlex
import subprocess
import sys

tools_dir = os.path.dirname(__file__)
tools_git_dir = os.path.join(tools_dir, ".git")
last_updated_path = os.path.join(tools_dir, ".last_updated")

manager = importlib.import_module("manager")

parser = argparse.ArgumentParser()
parser.add_argument("program_name", choices=manager.programs.keys())
parser.add_argument("-k", "--keep", dest="keep_old_files", help="keep old program versions", action="store_true", default=False)
parser.add_argument("-u", "--update-interval", dest="update_interval", help="how long to wait between update checks (in seconds) (-1 means never update)", type=int, default=3600)
parser.add_argument("-v", "--version", dest="program_version", help="use a specific version of the program", type=str, default="latest")
parser.add_argument("program_args", nargs=argparse.REMAINDER)

def run(**kwargs):
    update_tools(**kwargs)

    manager.update_programs(**kwargs)

    manager.run_program(**kwargs)

def update_tools(update_interval=3600, **kwargs):
    global manager

    if update_interval < 0:
        return

    if not os.path.isfile(os.path.join(tools_git_dir, "config")):
        print("Warning: 61c-tools is not a valid Git repo, updates may be skipped", file=sys.stderr)
        return

    status_output = subprocess.check_output(["git", f"--git-dir={tools_git_dir}", "status", "--porcelain"], cwd=tools_dir)
    if len(status_output) > 0:
        print("Warning: 61c-tools has unsaved changes, updates may be skipped", file=sys.stderr)
        return
    last_updated = None
    if os.path.isfile(last_updated_path):
        with open(last_updated_path, "r") as f:
            last_updated = datetime.fromisoformat(f.read())
    if last_updated and last_updated + timedelta(seconds=update_interval) >= datetime.now():
        return
    print(f"Updating 61c-tools...", file=sys.stderr)
    with open(last_updated_path, "w") as f:
        f.write(datetime.now().isoformat())
    subprocess.check_output(["git", f"--git-dir={tools_git_dir}", "fetch", "origin"], cwd=tools_dir)
    subprocess.check_output(["git", f"--git-dir={tools_git_dir}", "reset", "--hard", "origin/master"], cwd=tools_dir)

    manager = importlib.reload(manager)

if __name__ == "__main__":
    CS61C_TOOLS_ARGS = shlex.split(os.environ.get("CS61C_TOOLS_ARGS", ""))
    run(**vars(parser.parse_args(CS61C_TOOLS_ARGS + sys.argv[1:])))