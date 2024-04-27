import pandas as pd
import sys
import os
import subprocess
import shutil
from openai import OpenAI
from git import Repo
import errno

def log(text):
    try:
        if not os.path.exists("log.txt"):
            with open("log.txt", "w"):
                pass
        with open("log.txt", "a") as log_file:
            log_file.write(text + "\n")
    except Exception as e:
        print(f"Error occurred while writing to log.txt: {e}")


def clone_repository(repo_url, destination_folder):
    log(f"cloning repository: {repo_url} to folder: {destination_folder}\n")
    try:
        Repo.clone_from(repo_url, destination_folder)
    except Exception as e:
        log(f"Error cloning repository: {repo_url}\n")


def save_dependency_files_of_library_migrations(repository_folder, migration_folder, package_manager):
    if package_manager not in ["maven", "npm", "pypi"]:
        raise ValueError("package_manager must be one of 'maven', 'npm', 'pypi'")
    log(f"Checking commits from {repository_folder}\n")
    
    def commit_message_indicates_library_migration(commit_message):
        print(f"Checking commit message: {commit_message}")
        try:
            openai_client = OpenAI(api_key="sk-proj-7OQSCMJ1ACUV9f6wg8vcT3BlbkFJ1lp6KifftpuQ9qmIDL9g")
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are a helpful assistant that analyzes GitHub commit messages. You 
                    take commit messages as input, and if the commit message indicates a third-party library migration, you respond
                    with 'True', otherwise, you response with 'False'. Make sure not to classify merge commits as a library migration."""},          
                    {"role": "user", "content": f"{commit_message}"}
                ],
                temperature=1.00, 
                max_tokens=128
            )
            return True if response.choices[0].message.content == "True" else False
        except Exception as e:
            log(f"Error occured when calling GPT: {e}")
            print(f"Error occured when calling GPT: {e}")
            return False
    

    def save_dependency_files(repository_folder, dep_file, commit_hash, prev_commit_hash, commit_message):
        # Changing current working directory to parent directory instead of the cloned repo's directory
        try:
            current_dir = os.getcwd()
            parent_dir = os.path.dirname(current_dir)
            os.chdir(parent_dir)

            if not os.path.exists(migration_folder):
                os.makedirs(migration_folder)

            commit_hash_folder = os.path.join(migration_folder, commit_hash)
            os.makedirs(commit_hash_folder, exist_ok=True)
        except Exception as e:
            print("Error creating parent directory")
        try:
            shutil.copy2(f"{repository_folder}/{dep_file}", os.path.join(commit_hash_folder, f"{commit_hash}_{dep_file}"))
            shutil.copy2(f"{repository_folder}/{dep_file}", os.path.join(commit_hash_folder, f"prev_{prev_commit_hash}_{dep_file}"))
        except Exception as e:
            log(f"Error occured while copying dependency files: {e}")
        
        try:
            with open(f"{commit_hash_folder}/commit_message", "w") as f:
                f.write(commit_message)
        except Exception as e:
            log(f"Error occured while writing commit message to file: {e}")
    
        #Changing the current working directory back to the cloned repo's directory
        os.chdir(repository_folder)


    dep_file = { "maven": "pom.xml", "npm": "package.json", "pypi": "requirements.txt" }[package_manager]
    os.chdir(repository_folder)

    git_log_output = subprocess.check_output(['git', 'log', '--pretty=format:%H']).decode('utf-8')
    commits = git_log_output.strip().split("\n")
    for i in range(len(commits)):
        commit_hash = commits[i].strip()
        commit_message = subprocess.check_output(['git', 'log', '--format=%B', '-n', '1', commit_hash]).decode('utf-8')
        if i > 0 and commit_message_indicates_library_migration(commit_message):
            prev_commit_hash = commits[i-1].strip()
            print(f"saving dependency files for commit message: {commit_message}")
            save_dependency_files(repository_folder, dep_file, commit_hash, prev_commit_hash, commit_message)


def delete_cloned_repository(repository_folder):
    print(f"attempting to delete repository: {repository_folder}")
    try:
        shutil.rmtree(repository_folder)
    except OSError as e:
        log(f"Error deleting repository {repository_folder}")
        if e.errno == errno.EACCES:
            print(f"Permission error: Cannot delete {repository_folder}. Skipping deletion.")
        else:
            print(f"Other error encountered deleting {repository_folder}: {e}")
        

def main():
    if len(sys.argv) != 2:
        print("Usage: Python fetch_repos_metadata.py [maven/npm/pypi]")
        sys.exit(1)

    package_manager = sys.argv[1].lower()
    if package_manager == "maven":
        file = "mavenSample.csv"
        df = pd.read_csv(file, low_memory=False)
        for index, row in df.iterrows():
            if row["Platform"] != "Maven" or row["Language"] != "Java" or row["Repository.Language"] != "Java" or row["Repository.Host.Type"] != "GitHub":
                continue
            repo_name = row["Repository.Name.with.Owner"].split("/")[-1]
            repo_url = repo_url=row["Repository.URL"]
            if not repo_url.startswith("https://"):
                log(f"Skipping repo {repo_name} with url: {repo_url}")
                continue
            else:
                if os.path.exists(f"maven_migrations/{repo_name}_migrations"):
                    log(f"Skipping repo {repo_name} because a migration folder already exists for it.")
                    continue
                if not os.path.exists(repo_name):
                    print(f"repo already exists for {repo_name}")
                    os.makedirs(repo_name)
                    clone_repository(repo_url=repo_url, destination_folder=repo_name)
                if not os.path.exists(f"{repo_name}/pom.xml"):
                    log(f"Skipping {repo_name} because it does not contain pom.xml file.\n")
                    continue
                save_dependency_files_of_library_migrations(repository_folder=repo_name, migration_folder=f"maven_migrations/{repo_name}_migrations", package_manager="maven")
                current_dir = os.getcwd()
                parent_dir = os.path.dirname(current_dir)
                delete_cloned_repository(repository_folder=repo_name)
                os.chdir(parent_dir)

    elif package_manager == "npm":
        file = "npmSample.csv"
        df = pd.read_csv(file, low_memory=False)
        for index, row in df.iterrows():
            if row["Platform"] != "NPM" or row["Language"] != "JavaScript" or row["Repository.Language"] != "JavaScript" or row["Repository.Host.Type"] != "GitHub":
                continue
            repo_name = row["Repository.Name.with.Owner"].split("/")[-1]
            repo_url = repo_url=row["Repository.URL"]
            if not repo_url.startswith("https://"):
                log(f"Skipping repo {repo_name} with url: {repo_url}")
                continue
            else:
                if os.path.exists(f"npm_migrations/{repo_name}_migrations"):
                    log(f"Skipping repo {repo_name} because a migration folder already exists for it.")
                    continue
                if not os.path.exists(repo_name):
                    os.makedirs(repo_name)
                    clone_repository(repo_url=repo_url, destination_folder=repo_name)
                if not os.path.exists(f"{repo_name}/package.json"):
                    log(f"Skipping {repo_name} because it does not contain package.json file.\n")
                    continue
                save_dependency_files_of_library_migrations(repository_folder=repo_name, migration_folder=f"npm_migrations/{repo_name}_migrations", package_manager="npm")
                current_dir = os.getcwd()
                parent_dir = os.path.dirname(current_dir)
                delete_cloned_repository(repository_folder=repo_name)
                os.chdir(parent_dir)

    elif package_manager == "pypi":
        file = "pypiSample.csv"
        df = pd.read_csv(file, low_memory=False)
        for index, row in df.iterrows():
            if row["Platform"] != "Pypi" or row["Language"] != "Python" or row["Repository.Language"] != "Python" or row["Repository.Host.Type"] != "GitHub":
                continue
            repo_name = row["Repository.Name.with.Owner"].split("/")[-1]
            repo_url = repo_url=row["Repository.URL"]
            if not repo_url.startswith("https://"):
                log(f"Skipping repo {repo_name} with url: {repo_url}")
                continue
            else:
                if os.path.exists(f"pypi_migrations/{repo_name}_migrations"):
                    log(f"Skipping repo {repo_name} because a migration folder already exists for it.")
                    continue
                if not os.path.exists(repo_name):
                    os.makedirs(repo_name)
                    clone_repository(repo_url=repo_url, destination_folder=repo_name)
                if not os.path.exists(f"{repo_name}/requirements.txt"):
                    log(f"Skipping {repo_name} because it does not contain requirements.txt file.\n")
                    continue
                save_dependency_files_of_library_migrations(repository_folder=repo_name, migration_folder=f"pypi_migrations/{repo_name}_migrations", package_manager="pypi")
                current_dir = os.getcwd()
                parent_dir = os.path.dirname(current_dir)
                delete_cloned_repository(repository_folder=repo_name)
                os.chdir(parent_dir)

    else:
        print("Invalid argument. Please provide one of 'Maven', 'npm', 'pypi'")
        sys.exit(1)  


if __name__ == "__main__":
    main()