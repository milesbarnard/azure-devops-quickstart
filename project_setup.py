#!/usr/bin/python3

import argparse
import CICD_Providers.azure_devops as azure_devops_CICD
import Git_Providers.azure_devops as azure_devops_GIT

def main():
    parser = argparse.ArgumentParser(prog='Project Setup Utility', 
    description='Creates projects in Azure DevOps & Azure based on inputs The program will create \
        Git Repos, Build Pipelines, Deployment Pipelines & App services')

    subparser = parser.add_subparsers(dest='command')
    create = subparser.add_parser('create')
    delete = subparser.add_parser('delete') 

    create.add_argument('--project_name', help='The name of the project you wish to create', required=True, type=str,)
    create.add_argument('--personal_access_token', help='Your Azure DevOps personal access token', required=True, type=str)
    create.add_argument('--organisation_name', help='The name of your organisation in Azure Devops', required=True, type=str)
    create.add_argument('--azure_project_name', help='The name of your project in Azure Devops', required=True, type=str)
    create.add_argument('--user_email', help='Your ADO email address', required=True, type=str)
    create.add_argument('--environment_names', help='The list of environment names in your release pipelines', required=True, nargs='+')
    create.add_argument('--language',
                    default='dotnet',
                    const='dotnet',
                    nargs='?',
                    choices=['dotnet', 'dotnet-core', 'node-js', 'python'],
                    help='Language choices: dotnet, dotnet-core, node-js, python (default: %(default)s)')
    create.add_argument('--location', help='The list of environment names in your release pipelines', type=str)

    delete.add_argument('--project_name', help='The name of the project you wish to remove', required=True, type=str)
    delete.add_argument('--personal_access_token', help='Your Azure DevOps personal access token', required=True, type=str)
    delete.add_argument('--organisation_name', help='The name of your organisation in Azure Devops', required=True, type=str)
    delete.add_argument('--azure_project_name', help='The name of your project in Azure Devops', required=True, type=str)

    args = parser.parse_args()

    organization_url = 'https://dev.azure.com/' + args.organisation_name
    base_url = organization_url + '/' + args.azure_project_name

    build_pipeline = azure_devops_CICD.AzureDevops(args.azure_project_name, organization_url, args.personal_access_token)
    git_repo = azure_devops_GIT.AzureDevopsGitRepo(args.azure_project_name, args.personal_access_token, organization_url)

    if args.command == 'create':
        git_object = git_repo.createGitRepo(args.project_name)
        build_pipeline.createBuildPipeline(args.project_name, args.personal_access_token, git_object)
        build_pipeline.createReleasePipeline(args.project_name, args.environment_names, args.user_email)
        build_pipeline.createPipelinesTemplate(args.project_name, args.language)
    else:
        git_repo.deleteGitRepo(args.project_name)
        build_pipeline.deleteBuildPipeline(args.project_name, args.personal_access_token, base_url)
        build_pipeline.deleteReleasePipeline(args.project_name)

if __name__ == "__main__":
    main()