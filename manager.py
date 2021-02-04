from collections.abc import Iterable
from datetime import datetime, timedelta
import hashlib
import json
import os
import re
import requests
import sys
import time
import traceback

ISO_FORMAT_STRING = r"%Y-%m-%dT%H:%M:%S.%f"
BYTE_PREFIXES = {0: "", 1: "Ki", 2: "Mi", 3: "Gi"}
VERSION_URL = "https://inst.eecs.berkeley.edu/~cs61c-tar/tools/version.json"

tools_dir = os.path.join(os.path.dirname(__file__))
programs_dir = os.path.join(tools_dir, "programs")
version_file_path = os.path.join(tools_dir, "version.json")

class Program:
    def __init__(self, name, ext):
        self.name = name
        self.ext = ext
    def get_file_path(self, version):
        return os.path.join(programs_dir, f"{self.name}-{version}.{self.ext}")
    def get_run_args(self, **kwargs):
        version = get_version_data(self.name, **kwargs)["version"]
        if self.ext == "jar":
            return ["java", "-jar", self.get_file_path(version)]
        raise Exception(f"Unknown program type: {self.ext}")
    def get_version(self, filename):
        m = re.match(f"^{self.name}-([0-9][0-9a-z.-]+)\\.{self.ext}$", filename)
        if not m:
            return None
        return m.group(1)
    def get_installed_versions(self):
        versions = []
        try:
            for filename in os.listdir(programs_dir):
                if not os.path.isfile(os.path.join(programs_dir, filename)):
                    continue
                version = self.get_version(filename)
                if version:
                    versions.append(version)
        except FileNotFoundError:
            pass
        return versions
programs = {
    "logisim": Program("logisim", "jar"),
    "venus": Program("venus", "jar"),
}

def run_program(program_name, program_args=[], **kwargs):
    try:
        program = programs[program_name]
        args = program.get_run_args(**kwargs) + program_args

        os.execvp(args[0], args)
    except KeyboardInterrupt:
        pass

def update_programs(**kwargs):
    program_names = kwargs.pop("program_name", programs.keys())
    if not isinstance(program_names, Iterable) or isinstance(program_names, str):
        program_names = (program_names,)
    for program_name in program_names:
        update_program(program_name, **kwargs)

def update_program(program_name, keep_old_files=False, **kwargs):
    try:
        data = get_version_data(program_name, **kwargs)
        program = programs[program_name]

        other_vers = program.get_installed_versions()
        latest_ver = data["version"]
        if latest_ver not in other_vers:
            print(f"Updating {program_name} {other_vers} => {latest_ver}", file=sys.stderr)
            get_file(program.get_file_path(latest_ver), data["url"], data["sha256"])
            if not keep_old_files and len(other_vers) > 0:
                print(f"Removing {program_name} {other_vers}", file=sys.stderr)
                for other_ver in other_vers:
                    if other_ver != latest_ver:
                        try:
                            os.remove(program.get_file_path(other_ver))
                        except FileNotFoundError:
                            traceback.print_exc()
        else:
            other_vers.remove(latest_ver)
    except Exception as e:
        raise e

def get_version_data(program_name, program_version="latest", update_interval=3600, **kwargs):
    program_version_data = get_version_json(update_interval)[program_name]
    data = program_version_data[program_version]
    for i in range(256):
        if "ref" in data:
            data = program_version_data[data["ref"]]
            continue
        return data
    raise Execption("Encountered potential cycle when resolving versions")

def get_version_json(update_interval=3600):
    try:
        with open(version_file_path, "r") as f:
            _data = f.read()
            data = json.loads(_data)
            if update_interval < 0:
                return data
            if "_last_checked" in data:
                last_checked = datetime.strptime(data["_last_checked"], ISO_FORMAT_STRING)
                if last_checked + timedelta(seconds=update_interval) >= datetime.now():
                    return data
    except FileNotFoundError:
        pass
    except Exception as e:
        raise e
    if update_interval < 0:
        raise Exception("No version data saved, but updating is disabled")
    res = requests.get(VERSION_URL)
    data = res.json()
    data["_last_checked"] = datetime.now().isoformat()
    with open(version_file_path, "w") as f:
        f.write(json.dumps(data))
    return data

def fmt_bytes(size):
    power = 2 ** 10
    n = 0
    while size > power:
        size /= power
        n += 1
    return f"{size:.1f}{BYTE_PREFIXES[n]}B"

def get_file(path, url, expected_digest):
    try:
        os.mkdir(programs_dir)
    except FileExistsError:
        pass

    is_stderr_interactive = sys.stderr.isatty()

    temp_path = f"{path}.part"
    filename = os.path.basename(path)

    sys.stderr.write(f"Downloading {filename}...")
    sys.stderr.flush()
    response = requests.get(url, stream=True)
    response.raise_for_status()
    bytes_total = response.headers.get("content-length")
    sha256 = hashlib.sha256()

    with open(temp_path, "wb") as f:
        if bytes_total is None:
            data = response.content
            f.write(data)
            sha256.update(data)
            print(" OK", file=sys.stderr)
        else:
            bytes_written = 0
            bytes_total = int(bytes_total)
            last_perc = -1
            for data in response.iter_content(chunk_size=65536):
                bytes_written += len(data)
                f.write(data)
                sha256.update(data)
                perc = int(50 * bytes_written / bytes_total)
                if last_perc != perc:
                    if is_stderr_interactive:
                        sys.stderr.write(f"\r[{'=' * perc}{' ' * (50 - perc)}] {fmt_bytes(bytes_written):>8}/{fmt_bytes(bytes_total):<8} {filename}")
                        sys.stderr.flush()
                    last_perc = perc
            if is_stderr_interactive:
                sys.stderr.write("\n")
            else:
                sys.stderr.write(" Done\n")
            sys.stderr.flush()
        digest = sha256.hexdigest()
        if digest != expected_digest:
            raise Exception(f"Download failed: {filename} has bad checksum")
    os.rename(temp_path, path)
