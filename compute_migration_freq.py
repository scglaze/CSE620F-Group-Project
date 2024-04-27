import sys
import os
import subprocess
from git import Repo
import pandas as pd


def clone_repository(repo_url, destination_folder):
    print("Cloning repository", repo_url)
    print("Current working directory: ", os.getcwd())
    print(f"cloning repository: {repo_url} to folder: {destination_folder}\n")
    try:
        Repo.clone_from(repo_url, destination_folder)
    except Exception as e:
        print(f"Error cloning repository: {repo_url}\n")

def get_repo_url(repo_name, package_manager):
    print("Getting url for repo: ", repo_name)
    try:
        csv_file = f"{package_manager}Sample.csv"
        df = pd.read_csv(csv_file)
        mask = df["Repository.Name.with.Owner"].apply(lambda x: x.split("/")[-1] == repo_name)
        matching_row = df[mask]
        if len(matching_row) > 0:
            repository_url = matching_row.iloc[0]["Repository.URL"]
            return repository_url
        else:
            print(f"No matching repository found for '{repo_name}'.")
            return None
    except Exception as e:
        raise Exception(f"Error getting repo url: {e}")

def get_repo_name(folder_name):
    underscore_index = folder_name.find('_')
    if underscore_index != -1:
        substring = folder_name[:underscore_index]
        return substring
    else:
        return folder_name
    
def get_num_of_commits(repo_name, package_manager):
    print("getting num of commits for repo: ", repo_name)
    if os.path.exists(repo_name):
        os.chdir(repo_name)
    else:
        clone_repository(repo_url=get_repo_url(repo_name, package_manager), destination_folder=repo_name)
    log = subprocess.check_output(["git", "log", "--oneline"])
    commit_count = len(log.splitlines())
    print(f"num of commits for repo: {repo_name}: {commit_count}")
    current_dir = os.getcwd()
    parent_dir = os.path.dirname(current_dir)
    os.chdir(parent_dir)
    return commit_count

def get_num_of_migrations(folder):
    print("getting num of migrations from folder", folder)
    print("current working directory: ", os.getcwd())
    
    items = os.listdir(folder)
    subfolder_count = sum(os.path.isdir(os.path.join(folder, item)) for item in items)
    print(f"num of migrations for {folder}: {subfolder_count}")
    return subfolder_count

def write_migration_info_to_file(migration_info, package_manager):
    try:
        file_name = f"{package_manager}_migration_freq_info.txt"
        with open(file_name, "w") as file:
            file.write(migration_info)
        print(f"Migration info written to {file_name}")
    except Exception as e:
        print(f"Error writing migration info to file: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: Python compute_migration_freq.py [maven/npm/pypi]")
        sys.exit(1)

    package_manager = sys.argv[1].lower()
    if package_manager not in ["maven", "npm", "pypi"]:
        print("Invalid argument. Please provide one of 'Maven', 'npm', 'pypi'")
        sys.exit(1)  

    migration_folder = f"{package_manager}_migrations"

    if not os.path.exists(migration_folder):
        print(f"{migration_folder} is not a directory.")

    migration_count_info = ""
    for subfolder_name in os.listdir(migration_folder):
        subfolder_path = os.path.join(migration_folder, subfolder_name)
        if os.path.isdir(subfolder_path):
            repo_name = get_repo_name(subfolder_name)
            if not os.path.isdir(repo_name):
                clone_repository(get_repo_url(repo_name, package_manager), repo_name)
            num_commits = get_num_of_commits(repo_name, package_manager)
            num_migrations = get_num_of_migrations(f"{migration_folder}/{subfolder_name}")
            migration_count_info += f"Migration rate for {repo_name} = {num_migrations / num_commits}\n"
        else:
            print(f"{subfolder_path} is not a directory.")
    write_migration_info_to_file(migration_count_info, package_manager)

if __name__ == "__main__":
    main()