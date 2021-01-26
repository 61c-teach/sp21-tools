import os
import re
import subprocess
import sys
import traceback

ASSIGNMENT_NAME_REGEX = r"(\b|-|^)(lab|labs|proj[1-4])(\b|-|$)"
JAVA_VERSION_REGEX = r"^\w*(java|jdk)\s*version\s*\"([^\"]+)\""

tools_dir = os.path.dirname(__file__)
tools_git_dir = os.path.join(tools_dir, ".git")

issues = []

if not os.path.isfile(os.path.join(tools_git_dir, "config")):
    issues.append("Error: 61c-tools is not a valid Git repo")
else:
    print("61c-tools was cloned properly")

try:
    assignment_repo_names = []
    for name in os.listdir(os.path.dirname(tools_dir)):
        if re.search(ASSIGNMENT_NAME_REGEX, name):
            assignment_repo_names.append(name)
    if len(assignment_repo_names) < 2:
        issues.append("Error: did not find many assignment repos in parent directory")
    else:
        print(f"Found assignment repos: {assignment_repo_names}")
except:
    issues.append("Error: could not check for assignment repos in parent directory")
    traceback.print_exc()

try:
    java_version_out = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT)
    java_version_out = java_version_out.decode("utf-8", errors="ignore")
    try:
        match = re.match(JAVA_VERSION_REGEX, java_version_out)
        java_version = match[2]
        print(f"Java version: {java_version}")
    except:
        print(f"Unrecognized Java version string:\n{java_version_out}\n")
        raise Exception("Unrecognized Java version string")
except:
    issues.append("Error: Java check failed, is it installed and in your PATH?")
    traceback.print_exc()

if len(issues) == 0:
    print("Your 61c-tools install looks OK!")
else:
    print("Your 61c-tools install might have issues:")
    print("\n".join(issues))
    sys.exit(1)
