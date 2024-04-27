import xml.etree.ElementTree as ET
import sys
import os
import json


def write_dict_to_json(dictionary, filename):
    try:
        with open(filename, "w") as file:
            json.dump(dictionary, file, indent=4)
        print(f"Migration information successfully written to {filename}")
    except Exception as e:
        print(f"Error writing dictionary to json file: {e}")

def parse_pom(pom):
    try:
        tree = ET.parse(pom)
        root = tree.getroot()

        namespace = {'ns': 'http://maven.apache.org/POM/4.0.0'}
        dependencies = root.findall('.//ns:dependency/ns:artifactId', namespace)
        dependency_names = [dependency.text for dependency in dependencies]
        return dependency_names
    except Exception as e:
        print(f"Error reading pom.xml file '{pom}': {e}")
        return None
    
def parse_requirements(reqs):
    try:
        dependencies = []
        with open(reqs, "r") as file:
            for line in file:
                dependency_name = line.split('>', 1)[0].strip()
                dependencies.append(dependency_name)
        return dependencies
    except Exception as e:
        print(f"Error reading requirements.txt file '{reqs}': {e}")
        return None 

def parse_packagejson(package):
    try:
        ret = []
        with open(package, 'r') as file:
            data = json.load(file)
            dependencies = data.get('dependencies', {})
            for package_name in dependencies:
                ret.append(package_name)
        return ret
    except Exception as e:
        print(f"Error parsing package.json file '{package}': {e}")
        return None

def extract_deps(package_manager):
    master_migration_info = {}
    migration_folder = f"{package_manager}_migrations"
    for subfolder_name in os.listdir(migration_folder):
        subfolder_path = os.path.join(migration_folder, subfolder_name)
        if os.path.isdir(subfolder_path):
            migration_commits = os.listdir(subfolder_path)
            for commit in migration_commits:

                commit_info = os.listdir(os.path.join(subfolder_path, commit))
                prev_commit = ""
                mig_commit = ""
                for file in commit_info:
                    if file == "commit_message":
                        continue
                    elif file.startswith("prev"):
                        prev_commit = file
                    else:
                        mig_commit = file

                prev_commit_deps = []
                mig_commit_deps = []
                if package_manager == "maven":
                    parse_pom(os.path.join(subfolder_path, commit, prev_commit))
                    parse_pom(os.path.join(subfolder_path, commit, mig_commit))
                elif package_manager == "npm":
                    parse_packagejson(os.path.join(subfolder_path, commit, prev_commit))
                    parse_packagejson(os.path.join(subfolder_path, commit, mig_commit))
                elif package_manager == "pypi":
                    parse_requirements(os.path.join(subfolder_path, commit, prev_commit))
                    parse_requirements(os.path.join(subfolder_path, commit, mig_commit))

                if prev_commit_deps and mig_commit_deps:
                    prev_commit_deps_set = set(prev_commit_deps)
                    mig_commit_deps_set = set(mig_commit_deps)
                    abandonments = prev_commit_deps_set - mig_commit_deps_set
                    adoptions = mig_commit_deps_set - prev_commit_deps_set
                    for abandonment in abandonments:
                        if abandonment in master_migration_info:
                            master_migration_info[abandonment]["abandonments"] += 1
                        else:
                            master_migration_info[abandonment] = { "abandonments": 1, "adoptions": 0 }
                    for adoption in adoptions:
                        if adoption in master_migration_info:
                            master_migration_info[adoption]["adoptions"] += 1
                        else:
                            master_migration_info[adoption] = { "abandonments": 0, "adoptions": 1 }

    write_dict_to_json(master_migration_info, f"{migration_folder}_info.json")


def main():
    if len(sys.argv) != 2:
        print("Usage: Python compute_migration_freq.py [maven/npm/pypi]")
        sys.exit(1)

    package_manager = sys.argv[1].lower()
    if package_manager not in ["maven", "npm", "pypi"]:
        print("Invalid argument. Please provide one of 'Maven', 'npm', 'pypi'")
        sys.exit(1)  

    extract_deps(package_manager)

if __name__ == "__main__":
    main()