import requests
import json
import os
import shutil

from azure.devops.connection import Connection
from azure.devops.v6_0 import task_agent
from azure.devops.v6_0.task_agent.models import TaskAgentQueue
from azure.devops.v5_1.task_agent.models import TaskAgentPoolReference
from azure.devops.v6_0.release.models import ApprovalOptions
from msrest.authentication import BasicAuthentication
from datetime import datetime
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
from git import Repo

class AzureDevops:
    def __init__(self, project_name, organization_url, personal_access_token):
        self.personal_access_token = personal_access_token
        self.credentials = BasicAuthentication('', personal_access_token)
        self.connection = Connection(base_url=organization_url, creds=self.credentials)
        self.core_client = self.connection.clients.get_core_client()
        self.project_info = self.getProject(project_name)
        self.project_last_update_time = self.getProjectLastUpdateTime(organization_url, personal_access_token)
        self.pool = self.getAgentPool(self.connection)
        self.queue = self.getOrCreateQueue(organization_url, self.pool)
        self.build_definition_url = organization_url + '/' + project_name + '/_apis/build/definitions?api-version=6.0'
        self.organization_url = organization_url
        self.organization_name = urlparse(organization_url).path.split('/')[-1]
    
    def createPipelinesTemplate(self, name, language):
        HTTPS_REMOTE_URL = 'https://' + self.organization_name + ':' + self.personal_access_token + '@dev.azure.com/' + self.organization_name + '/' + self.project_info.name + '/_git/' + name
        
        project_repo = Repo.clone_from(HTTPS_REMOTE_URL, 'script_repo')
        template_repo = Repo.clone_from('https://github.com/microsoft/azure-pipelines-yaml.git', 'template_repo')

        new_file_path = os.path.join(project_repo.working_tree_dir, 'azure-pipelines.yml')

        switch = {
            "dotnet": "asp.net.yml",
            "dotnet-core": "asp.net-core.yml",
            "node-js": "node.js.yml",
            "python" : "python-package.yml"
            }
            
        template_file_path = os.path.join(template_repo.working_tree_dir, 'templates/' + switch.get(language))
        data = ""
    
        shutil.copyfile(template_file_path, new_file_path)

        
        with open(new_file_path, 'r') as myfile:
            data = myfile.read()

        with open(new_file_path, 'w') as myfile:
            data = data.replace("{{ branch }}", "master")
            myfile.write(data)

        try:
            with open(new_file_path, 'w') as myfile:
                data = data.replace("{{ pool }}", "vmImage: ubuntu-latest")
                myfile.write(data)
        except:
            print("Pool property not present")

        try:
            project_repo.git.add(all=True)
            project_repo.index.commit("Added azure-pipelines.yml")
            origin = project_repo.remote(name='origin')
            origin.push()
        except:
            print('Some error occured while pushing the code')    

        shutil.rmtree('./script_repo')
        shutil.rmtree('./template_repo')
    
    def createReleasePipeline(self, name, environment_names, user_email):
        build_client = self.connection.clients.get_build_client()
        definition_id = self.getDefinitionIdForDelete(build_client, name)
        
        request = {}
        request['name'] = name
        request['source'] = "restApi"
        request['revision'] = 1
        description = "Build by project_setup.py"
        request['description'] = description
        request['createdBy'] = None
        createdOn = (datetime.now().isoformat())[:-3] + 'Z'
        request['createdOn'] = createdOn
        request['modifiedBy'] = None
        modifiedOn = (datetime.now().isoformat())[:-3] + 'Z'
        request['modifiedOn'] = modifiedOn
        request['isDeleted'] = False
        request['variables'] = {}
        request['variableGroups'] = []
        environments = self.createEnvironments(environment_names, user_email, name)
        request['environments'] = environments
        request['artifacts'] = [{
            "sourceId": str(self.project_info.id) + ":" + str(definition_id),
            "type": "Build",
            "alias": "_" + name,
            "definitionReference": {
            "artifactSourceDefinitionUrl": {
                "id": "https://dev.azure.com/" + self.organization_name + "/_permalink/_build/index?projectId=" + str(self.project_info.id) + "&definitionId=" + str(definition_id),
                "name": ""
            },
            "defaultVersionBranch": {
                "id": "",
                "name": ""
            },
            "defaultVersionSpecific": {
                "id": "",
                "name": ""
            },
            "defaultVersionTags": {
                "id": "",
                "name": ""
            },
            "defaultVersionType": {
                "id": "latestType",
                "name": "Latest"
            },
            "definition": {
                "id": "" + str(definition_id),
                "name": str(self.organization_name)
            },
            "definitions": {
                "id": "",
                "name": ""
            },
            "IsMultiDefinitionType": {
                "id": "False",
                "name": "False"
            },
            "project": {
                "id": str(self.project_info.id),
                "name": self.project_info.name
            },
            "repository": {
                "id": "",
                "name": ""
            }
            },
            "isPrimary": True,
            "isRetained": False
        }]
        request['triggers'] = [{"artifactAlias": "_" + name ,"triggerConditions":[{"sourceBranch":"master","tags":[],"tagFilter":None,"useBuildDefinitionBranch":False,"createReleaseOnBuildTagging":False}],"triggerType":"artifactSource"}]
        request['releaseNameFormat'] = None
        request['tags'] = []
        request['properties'] = {}
        request['projectReference'] = None
        request['_links'] = {}

        url = "https://vsrm.dev.azure.com/" + self.organization_name + '/' + self.project_info.name + "/_apis/release/definitions?api-version=6.0"
        headers = {'Content-type': 'application/json'}
        auth=HTTPBasicAuth('user', self.personal_access_token)
        request = requests.post(url, auth=auth, data=json.dumps(request), headers=headers)
        print(request.text)
    
    def createEnvironments(self, names, user_email, definition_name):
        release_client = self.connection.clients.get_release_client()
        environment_list = []
        environment_ids = []

        for x in release_client.get_release_definitions(project=self.project_info.id).value:
            environment_ids.append(max(i.id for i in release_client.get_release_definition(project=self.project_info.id, definition_id=x.id).environments))
        environment_id = max(environment_ids)

        auth=HTTPBasicAuth('user', self.personal_access_token)
        userIds = requests.get("https://vssps.dev.azure.com/" + self.organization_name + "/_apis/graph/users?api-version=5.0-preview.1", auth=auth)
        
        userIds = json.loads(userIds.text)
        userDefinition = {}
        for x in userIds['value']:
            if x['principalName'].lower() == user_email.lower():
                userDefinition = x
        user_descriptor = urlparse(userDefinition['url']).path.split('/')[-1]

        userEntitlement = requests.get('https://vsaex.dev.azure.com/' + self.organization_name + '/_apis/userentitlements/' + user_descriptor + '?api-version=6.0', auth=auth)
        userEntitlement = json.loads(userEntitlement.text)
        user_id = userEntitlement['id']
        owner = json.loads('{ "displayName": "", "url": "", "_links": {"avatar": {"href": ""}},"id": "","uniqueName": "","imageUrl": "","descriptor": ""}')
        owner['displayName'] = user_email
        owner['uniqueName'] = user_email
        owner['id'] = user_id
        owner['url'] = self.organization_url + '/_apis_Identities/' + user_id
        owner['_links']['avatar']['href'] = 'https://' + self.organization_url + '/_apis/GraphProfile/MemberAvatars/' + user_descriptor
        owner['imageUrl'] = self.organization_url + '/_api/_common/identityImage?id=' + user_id
        owner['descriptor'] = user_descriptor

        rank = 0
        for name in names:
            rank = rank + 1
            deploy_rank = 1
            environment_id = environment_id + 1
            environment = {}
            environment['id'] = environment_id
            environment['name'] = name
            environment['retentionPolicy'] = json.loads('{"daysToKeep": 30, "releasesToKeep": 3, "retainBuild": true}')
            environment['preDeployApprovals'] = json.loads('{"approvals": [{"rank": ' + str(deploy_rank) +',"isAutomated": false,"isNotificationOn": false,"approver": {"displayName": null,"id": "aeb95c63-4fac-4948-84ce-711b0a9dda97"},"id": ' + str(environment_id) + '}]}')
            approval_options = ApprovalOptions()
            environment['postDeployApprovals'] = json.loads('{"approvals": [{"rank": ' + str(deploy_rank) + ',"isAutomated": true,"isNotificationOn": false,"id": '+ str(environment_id) + '}], "approvalOptions": {"requiredApproverCount": null,"releaseCreatorCanBeApprover": false,"autoTriggeredAndPreviousEnvironmentApprovedCanBeSkipped": false,"enforceIdentityRevalidation": false,"timeoutInMinutes": 0,"executionOrder": "afterSuccessfulGates"}}')
            environment['deployPhases'] = json.loads('[{"deploymentInput": {"agentSpecification": {"identifier": "vs2017-win2016"}, "parallelExecution": {"parallelExecutionType": "none"},"skipArtifactsDownload": false,"artifactsDownloadInput": {},"queueId": ' + str(self.queue.id) + ',"demands": [],"enableAccessToken": false,"timeoutInMinutes": 0,"jobCancelTimeoutInMinutes": 1,"condition": "succeeded()","overrideInputs": {} },"rank": ' + str(deploy_rank) +',"phaseType": "agentBasedDeployment","name": "Run on agent","workflowTasks": []}]')
            environment['environmentOptions'] = json.loads('{"emailNotificationType": "OnlyOnFailure","emailRecipients": "release.environment.owner;release.creator","skipArtifactsDownload": false,"timeoutInMinutes": 0,"enableAccessToken": false,"publishDeploymentStatus": false,"badgeEnabled": false,"autoLinkWorkItems": false,"pullRequestDeploymentEnabled": false}')
            environment['demands'] = []
            environment['conditions'] = [{
                "name": "_" + definition_name,
                "conditionType": "artifact",
                "value": "{\"sourceBranch\":\"master\",\"tags\":[],\"useBuildDefinitionBranch\":false,\"createReleaseOnBuildTagging\":false}"
                }]
            if rank == 1:
                environment['conditions'].append({
                "name": "ReleaseStarted",
                "conditionType": "event",
                "value": ""
                })
            else:
                environment['conditions'].append({
                "name": names[names.index(name) - 1],
                "conditionType": "environmentState",
                "value": "4"
                })
            environment['executionPolicy'] = json.loads('{"concurrencyCount": 0,"queueDepthCount": 0}')
            environment['schedules'] = []
            environment['retentionPolicy'] = json.loads('{"daysToKeep": 30,"releasesToKeep": 3,"retainBuild": true}')
            environment['properties'] = {"properties": {
                "LinkBoardsWorkItems": {
                "$type": "System.String",
                "$value": "False"
                }
            }}
            environment['preDeploymentGates'] = json.loads('{"id": ' + str(environment_id) +',"gatesOptions": null,"gates": []}')
            environment['postDeploymentGates'] = json.loads('{"id": ' + str(environment_id) +',"gatesOptions": null,"gates": []}')
            environment['environmentTriggers'] = []
            environment['rank'] = rank
            environment['owner'] = owner
            environment_list.append(environment)
        return environment_list
    
    def deleteReleasePipeline(self, release_pipeline_name):
        print("Removing release pipeline")
        release_client = self.connection.clients.get_release_client()
        environment_id = 0
        for x in release_client.get_release_definitions(project=self.project_info.id).value:
            if x.name == release_pipeline_name:
                environment_id = x.id
                error_text = ""
            else:
                error_text = "An error occured - could not find release pipeline id"
        print(error_text)

        url = "https://vsrm.dev.azure.com/" + self.organization_name + '/' + self.project_info.name + "/_apis/release/definitions/" + str(environment_id) + "?api-version=6.0"
        auth=HTTPBasicAuth('user', self.personal_access_token)
        requests.delete(url, auth=auth)
        

    # Reasoning behind using requests instead of the Python SDK found here: https://developercommunity.visualstudio.com/t/api-documentation-out-of-date/1437337
    def createBuildPipeline(self, name, personal_access_token, git_repo):
        data = {
                "folder": None,
                "name": name,
                "configuration": {
                    "type": "yaml",
                    "path": "/azure-pipelines.yml",
                    "repository": {
                    "id": git_repo.repo_id,
                    "name": git_repo.full_name,
                    "type": "azureReposGit"
                    }
                }
            }

        headers = {'Content-type': 'application/json'}
        auth=HTTPBasicAuth('user', personal_access_token)
        request = requests.post("https://dev.azure.com/" + self.organization_name + "/" + self.project_info.name + "/_apis/pipelines?api-version=6.0", json.dumps(data), headers=headers, auth=auth)

    def deleteBuildPipeline(self, name, personal_access_token, base_url):
        build_client = self.connection.clients.get_build_client()
        definition_id = self.getDefinitionIdForDelete(build_client, name)
        build_definition_url = base_url + '/_apis/build/definitions/' + str(definition_id) + '?api-version=6.0'
        auth=HTTPBasicAuth('user', personal_access_token)
        requests.delete(build_definition_url, auth=auth)

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

    def getRepoId(self, git_client, name):
        repo_id = git_client.get_repository(name, project=self.project_info.id)
        repo_id = repo_id.id
        return repo_id

    def getDefinitionId(self, build_client):
        definitions = build_client.get_definitions(project=self.project_info.id)
        definition_max = max(definition.id for definition in definitions.value)
        definition_id = definition_max + 1
        return definition_id

    def getDefinitionIdForDelete(self, build_client, name):
        definitions = build_client.get_definitions(project=self.project_info.id, name=name)
        definition_id = list(definition.id for definition in definitions.value)[0]
        return(definition_id)

    def getProject(self, project_name):
        project = self.core_client.get_projects(project_name)
        for value in project.value:
            if value.name == project_name:
                project_info = value
                return project_info
    
    def getProjectLastUpdateTime(self, organization_url, personal_access_token):
        auth = HTTPBasicAuth('user', personal_access_token)
        url = organization_url + '/_apis/projects/' + self.project_info.id + '?api-version=6.0'
        project = requests.get(url, auth=auth)
        project_json = json.loads(project.text)
        return project_json['lastUpdateTime']

    def getAgentPool(self, connection):
        task_agent_client = connection.clients.get_task_agent_client()
        pools = task_agent_client.get_agent_pools()
        pool_list = list(x for x in pools)
        if 'Azure Pipelines' in list(x.name for x in pools):
            for item in pool_list:
                if item.name == 'Azure Pipelines':
                    return item
        else:
            print("A problem has occured - default azure hosted pipeline not found")
        
    def getOrCreateQueue(self, organization_url, pool):
        client = task_agent.TaskAgentClient(base_url=organization_url, creds=self.credentials)
        queues = client.get_agent_queues(self.project_info.id)
        queue_list = list(x for x in queues)
        if 'Azure Pipelines' in list(x.name for x in queues):
            for item in queue_list:
                if item.name == 'Azure Pipelines':
                    return item
        else:
            print('Creating a new agent queue')
            reference = TaskAgentPoolReference(id=pool.id, is_hosted=pool.is_hosted, is_legacy=pool.is_legacy,
                                                name=pool.name, pool_type=pool.pool_type, scope=pool.scope, size=pool.size)
            new_queue = TaskAgentQueue(id=(max(x.id for x in queues)) + 1, name="Azure Pipelines", pool=reference, project_id=self.project_info.id )
            client.add_agent_queue(new_queue, project=self.project_info.id)