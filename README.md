# Introduction 
This project is to aid with the quick set up of CI/CD pipelines for Azure Devops. Invoking this command will do the following:
 - Set up a Git repository
 - Set up a build pipeline with a YAML template for dotnet, dotnet-core, python or node.js
 - Set up a deployment pipeline with n stages, link the artifact and stages together

# Getting Started
1.	Installation process: 

    On Linux:
    ```
    git clone https://github.com/milesbarnardw2/azure-devops-quickstart.git
    cd azure-devops-quickstart
    python3 -m pip install --user virtualenv
    python3 -m venv env
    source env/bin/activate
    pip install -r ./requirements.txt
    ```
2.	Software dependencies: Python3, Git
3.	Usage:

    Links:
    - To generate personal access token: https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate?view=azure-devops&tabs=preview-page#create-a-pat
    - Find organisation name and project:
        Sign into Azure DevOps
        Look at the URL - the format is as follows: https://dev.azure.com/{yourorganization} - yourorganisation is your organisation name
        Click on the project you plan to deploy to
        Look at the URL - https://dev.azure.com/{yourorganization}/{yourproject} - yourproject is the azure project name


    To create a pipeline (from within virtual environment created above):
    
    ```
    python3 project_setup.py create \
        --project_name "<the name of your project>" \
        --personal_access_token "<your azure devops personal access token>" \
        --organisation_name "<azure devops organisation name>" \
        --azure_project_name "<azure devops project name>" \
        --environment_names "dev" "<any number of environments after this>" \
         --user_email "<your azure devops email>"
    ```

    To remove a pipeline:
    ```
    python3 project_setup.py delete \
        --project_name "<the name of your project>" \
        --personal_access_token "<azure devops personal access token>" \
        --organisation_name "<azure devops organisation name>" \
        --azure_project_name "<azure devops project name>"
    ```
4.  API References:


# Contribute
TODO: Explain how other users and developers can contribute to make your code better. 
