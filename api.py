import requests, json, os
import inquirer #for ease of data entry in cli
import click
import pprint

url ="https://interviewt.jfrog.io/artifactory"

def create_token(entered_username, entered_password):
    auth_url = "https://interviewt.jfrog.io/access/api/v1/tokens"

    response = requests.post(auth_url, auth=(entered_username, entered_password), data={"scope": "applied-permissions/admin"})

    if response.status_code == 200:
        print("Access token successfully created.")
        token_data = response.json()
        token = token_data.get("access_token")
        return token
    else:
        print(f"Authentication failed: {response.status_code} - {response.text}")
        return None

def login_cli():
    print("Welcome to Justine's CLI!")

    attempts = 3
    
    while (attempts>0):
        entered_username = input("CLI username: ")
        entered_password = input("CLI password: ")
        token = create_token(entered_username, entered_password)
        if token: #if successful
            return token
        else:
            attempts-=1
            print (f"Invalid credentials.{attempts} attempts left") 
    
    # print("Too many failed atempts. Exiting.")
    return None

def system_ping(url,token):
    authorizationheader = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{url}/api/system/ping", headers=authorizationheader)
    if response.status_code == 200:
        print("System is up & running!")
    else:
        print(f"Ping failed: {response.text}")
    
def system_version(url,token):
    systemresponse = requests.get(f"{url}/api/system/ping", headers={"Authorization": f"Bearer {token}"})
    print(systemresponse.headers['X-JFrog-Version'])
    
def create_user(token,url):
    #Prompts to the user
    q = [
    inquirer.Text(name ='username', message="*No capital letters* Please enter your username."),
    inquirer.Text(name ='email', message="Please enter your email."),
    inquirer.Text(name ='password', message="Please enter your password. It should include: 1 uppercase letter, 1 lowercase letter, 1 digit, 1 special character & be at least 8 characters long"),
    inquirer.List(name ='admin', message="Is this an admin role?", choices=["Yes", "No"], default="No")
    ]

    newuserdata = inquirer.prompt(q)
    # Prepare user data
    if newuserdata['admin'] == "Yes":
        admindata = True
    else:
        admindata = False

    user_data = {
        "username": newuserdata['username'],
        "password": newuserdata['password'],
        "email": newuserdata['email'],
        "admin": admindata
    }
    
    headers = {"X-JFrog-Art-Api": f"bearer {token}", "Content-Type": "application/json"}
    response = requests.put(f"{url}/access/api/v2/users/{newuserdata['username']}", headers = headers, data=json.dumps(newuserdata))
    
    #does the user already exist?
    if response.status_code == 201:
        click.echo(f"User '{newuserdata['username']}' created successfully!")
    elif response.status_code == 409:
        click.echo(f"User already exists.")
    else:
        click.echo(f"Failed to create user: {response.status_code} - {response.text}")

def delete_user(token):
    q = [inquirer.Text(name='username', message="*Delete User* Enter the username")]
    user_data = inquirer.prompt(q)
    username = user_data['username']
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.delete("https://interviewt.jfrog.io/access/api/v1/users/{username}", headers=headers)
    if response.status_code == 200:
        print(f"User '{username}' deleted successfully.")
    elif response.status_code == 404:
        print(f"User '{username}' not found.")
    elif response.status_code == 403:
        print(f"Insufficient permissions to delete user '{username}'.")
    else:
        print(f"Failed to delete user: {response.status_code} - {response.text}")

def storage_info(token,url):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url+"/api/storageinfo", headers=headers)
    if response.status_code == 200:
        pprint.pprint(response.json())
    else:
        click.echo(f"Error {response.status_code}:{response.text}")

def create_repo(token, url):
    #prompt user to enter new repository details such as title, class, package type
    q = [
        inquirer.Text(name ='key', message="New Repository Name/Key"),
        inquirer.List(name ='Repoclass', message="Class", choices=["local", "remote", "virtual", "federated"], default="local"),
        inquirer.List('packageType', message="Select the package type",
            choices=['generic', 'maven', 'gradle', 'ivy', 'sbt', 'helm', 'cocoapods',
                'opkg', 'rpm', 'nuget', 'cran', 'gems', 'npm', 'bower', 'debian',
                'composer', 'pypi', 'docker', 'vagrant', 'gitlfs', 'go', 'yum',
                'conan', 'chef', 'puppet', 'conda', 'terraform', 'ansible',
                'carthage', 'swift', 'chocolatey', 'distsign'],default = 'generic' )
     ]
    answers = inquirer.prompt(q)
    remote_url = ""

    if answers['Repoclass'] == 'remote':
        remoteanswer= inquirer.prompt([inquirer.Text(name ='remoteurl', message="Enter remote url")])
        remote_url = remoteanswer['remoteurl']
   
    exist = does_repo_exist(token,url,answers)  #Check first if Repository already exists before creating one
    if exist==True:
        print(f"Repository {answers['key']} already exists.")
        #go back to main menu
        return
    elif exist==False:
        #continue to create repository 
        payload = {
            "rclass": answers['Repoclass'],
            "packageType": answers['packageType'],
            "url" : remote_url
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.put(f"{url}/api/repositories/{answers['key']}", headers=headers, data=json.dumps(payload))
        if response.status_code == 200 or 201:
            print(f"Repository '{answers['key']}' created successfully.")
        else:
            print(f"Error {response.status_code}: {response.text}")

def does_repo_exist(token,url,answers):
    existence_header = {"Authorization": f"Bearer {token}"}
    existence = requests.get(f"{url}/api/repositories/{answers['key']}", headers=existence_header)
    if existence.status_code == 200:
        #Repository exists 
        return True
    elif existence.status_code == 400: 
        # Repository does not exist
         return False
    else:
        raise Exception(f"Error {existence.status_code}: {existence.text}")

def list_all_repositories(token,url):
    listheader = {"Authorization": f"Bearer {token}"}
    repositories = requests.get(f"{url}/api/repositories", headers=listheader)
    if repositories.status_code == 200:
        pprint.pprint(repositories.json())
    else:
        click.echo(f"Error {repositories.status_code}:{repositories.text}")

def update_repo(token,url):
    initial_urq = [
        inquirer.Text(name ='key', message="Enter Repository Name you would like to update"),
        inquirer.List(name='updateordelete',message="Would you like to update or delete the repository?", choices=['Update','Delete'])
    ]
    answers = inquirer.prompt(initial_urq)
    payload = {}
    end=True

    if answers['updateordelete'] == "Update":
        if does_repo_exist(token,url,answers) == True:
            while end:
                updateq=inquirer.prompt([inquirer.List(name='updatechoice', 
                    message="Select what change to the repository you would like to make",
                    choices=["Description","Notes","Include Pattern","Exclude Pattern",
                             "Repository Layout","Xray Index","Priority Resolution"])])
                
                if updateq['updatechoice'] == "Description":
                    description = inquirer.prompt([inquirer.Text(name='description', message="Enter new description")])
                    payload["description"] = description['description']
                    if click.confirm('Thank you. Do you need to make another change?'):
                        end=True
                    else:
                        end =False
                elif updateq['updatechoice'] == "Notes":
                    notes = inquirer.prompt([inquirer.Text(name='notes', message="Enter new notes")])
                    payload["notes"] = notes['notes']
                    if click.confirm('Thank you. Do you need to make another change?'):
                        end=True
                    else:
                        end =False
                elif updateq['updatechoice'] == "Includes Pattern":
                    includes_pattern = inquirer.prompt([inquirer.Text(name='includesPattern', message="Enter new includes pattern")])
                    payload["includesPattern"] = includes_pattern['includesPattern']
                    if click.confirm('Thank you. Do you need to make another change?'):
                        end=True
                    else:
                        end =False
                elif updateq['updatechoice'] == "Excludes Pattern":
                    excludes_pattern = inquirer.prompt([inquirer.Text(name='excludesPattern', message="Enter new excludes pattern")])
                    payload["excludesPattern"] = excludes_pattern['excludesPattern']
                    if click.confirm('Thank you. Do you need to make another change?'):
                        end=True
                    else:
                        end =False
                elif updateq['updatechoice'] == "Repo Layout":
                    repo_layout = inquirer.prompt([inquirer.Text(name='repoLayoutRef', message="Enter new repo layout reference")])
                    payload["repoLayoutRef"] = repo_layout['repoLayoutRef']
                    if click.confirm('Thank you. Do you need to make another change?'):
                        end=True
                    else:
                        end =False
                elif updateq['updatechoice'] == "Xray Index":
                    if click.confirm('Enable Xray indexing?'):
                        xray_index = True
                        print ("Xray Indexing Enabled)")
                    else:
                        xray_index = False
                    payload["xrayIndex"] = xray_index
                    if click.confirm('Thank you. Do you need to make another change?'):
                        end=True
                    else:
                        end =False
                elif updateq['updatechoice'] == "Priority Resolution":
                    if click.confirm('Enable Priority Resolution?'):
                        priority_resolution = True
                    else:
                        priority_resolution = False
                    payload["priorityResolution"] = priority_resolution
                    if click.confirm('Thank you. Do you need to make another change?'):
                        end=True
                    else:
                        end =False
               
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            response = requests.put(f"{url}/api/repositories/{answers['key']}", headers=headers, data=json.dumps(payload))
            if response.status_code == 200 or 201:
                print(f"Repository '{answers['key']}' updated successfully.")
            else:
                print(f"Error {response.status_code}: {response.text}")
        else:
            print(f"Repository {answers['key']} does not exist. Cannot update.")
            return
    else:
        deleterepo(token,url,answers)       

def deleterepo(token,url,answers):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(f"{url}/api/repositories/{answers['key']}", headers=headers)
    if response.status_code == 200:
        print(f"Repository '{answers['key']}' deleted successfully.")
    else:
        print(f"Error {response.status_code}: {response.text}")
    return

def mainmenu():
    q = [inquirer.List(name ='choice', 
                           message="What task would you like performed?", 
                           choices=["System Ping", "Get System Version", "Get Storage Info",
                                    "Create Repository","Update/delete Repository","List repositories","Delete User", "Help"])]
    choicedata = inquirer.prompt(q) 
    return choicedata['choice']

def help_menu():
    help_text = {
        "System Ping": "Checks if the Artifactory system is up and running.",
        "Get System Version": "Retrieves the current version of the Artifactory system.",
        "List Repositories": "Lists all repositories in the Artifactory instance.",
        "Create Repository": "Creates a new repository in Artifactory.",
        "Update/Delete Repository": "Updates or deletes an existing repository.",
        "Create User": "Adds a new user to the Artifactory system.",
        "Delete User": "Deletes a specified user from the Artifactory system.",
    }
    q = [inquirer.List('choice',
        message="Select a command to see details:",
        choices=list(help_text.keys()))]
    
    choice = inquirer.prompt(q)['choice']
    print(f"{choice}:\n{help_text[choice]}")

if __name__ == "__main__":
    token = login_cli()
    if not token:
        print("Failed to log in. Exiting.")
        exit()
    while True:
        choicedata = mainmenu()
        if (choicedata == "Help"):
            help_menu()
        elif (choicedata== 'System Ping'):
            system_ping(url,token)
        elif (choicedata == 'Get System Version'):
            system_version(url,token)
        elif (choicedata == "Get Storage Info"):
            storage_info(token,url)
        elif (choicedata == "Create Repository"):
            create_repo(token,url)
        elif (choicedata == "Update/delete Repository"):
            update_repo(token,url)
        elif (choicedata == "List repositories"):
            list_all_repositories(token,url)
        elif (choicedata == "Delete User"):
            delete_user(token)
        else:
            print ("Invalid. Try again.")
 
        # Ask if the user wants to perform another task
        if not click.confirm('Do you need to do another command?'):
            print("Exiting the CLI. Goodbye!")
            break

  