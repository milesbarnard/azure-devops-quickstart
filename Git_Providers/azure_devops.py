import sys
from azure.devops.v6_0.git.models import GitRepositoryCreateOptions
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from . import models as local_models

class AzureDevopsGitRepo:
    def __init__(self, azure_project_name, personal_access_token, organization_url):
        self.credentials = BasicAuthentication('', personal_access_token)
        self.connection = Connection(base_url=organization_url, creds=self.credentials)
        self.core_client = self.connection.clients.get_core_client()
        self.azure_project_info = self.getProject(azure_project_name)
        self.git_client = self.connection.clients.get_git_client()

    def createGitRepo(self, name):
        repos = self.git_client.get_repositories(self.azure_project_info.id)

        if not any(repo.name == name for repo in repos):
            print("Creating new git repo: " + name)
            repo = GitRepositoryCreateOptions(name=name)
            self.git_client.create_repository(repo, project=self.azure_project_info.id)
            repo = self.getRepo(name)
            git_repo = local_models.GitRepo(full_name=repo.name, url=repo.web_url, default_branch=repo.default_branch, is_fork=repo.is_fork, repo_id=repo.id)
            return(git_repo)
        else:
            print("Repository " + name + " already exists")
    
    def deleteGitRepo(self, name):
        repos = self.git_client.get_repositories(self.azure_project_info.id)
        repo = self.getRepo(name) 

        if any(repo.name == name for repo in repos):
            answer = self.yes_no("Are you sure? Please confirm deletion by typing project name or no [project_name/n]\n", name)
            if answer:
                print("Removing git repo: " + name)
                self.git_client.delete_repository(repo.id, project=self.azure_project_info.id)
            else:
                sys.exit("Program exited by user")
        else:
            print("Git repository " + name +  " does not exist")

    def getRepo(self, name):
        repo = self.git_client.get_repository(name, project=self.azure_project_info.id)
        return repo

    def getProject(self, project_name):
        project = self.core_client.get_projects(project_name)
        for value in project.value:
            if value.name == project_name:
                azure_project_info = value
                return azure_project_info

    def yes_no(self, answer, name):
        name = name.lower()
        yes = set([name])
        no = set(['no','n'])
        
        while True:
            choice = input(answer).lower()
            if choice in yes:
                return True
            elif choice in no:
                return False
            else:
                print("Please respond with project_name or 'no'")