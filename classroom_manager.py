import json
import shutil
from github import Github
from git import Repo
import time

# REFERENCE
#----------------------------------------------------------------------------------------------
# Oauth tokens in gitpython    
# http://stackoverflow.com/questions/36358808/cloning-a-private-repo-using-https-with-gitpython
# User: shawnzhu
#
# Organizations & Membership
# https://github.com/PyGithub/PyGithub/issues/507
# User: lbrownell-gpsw
#----------------------------------------------------------------------------------------------

class Manager():
    def __init__(self, name):
        self.name = name
        self.url = "https://github.com/{}/".format(name)
        token = self.get_token()
        self.hub = Github(token)        
        self.org = self.hub.get_organization(name)

    # Purpose:
    #   Reads git.token to get the oauth token that allows PyGithub and GitPython 
    #   to perform their actions.
    def get_token(self):
        f = open("git.token", "r")
        token = f.read().strip()
        return token

    # Params:
    #   hub: PyGitHub github object
    #   name: the name of the organization being retrieved
    # Purpose:
    #   Get access to the PyGitHub abstraction of the classroom
    # Returns:
    #   An instance of PyGitHub abstraction of the GitHub service
    def get_org(self):
        print self.hub
        return self.hub.get_organization(self.name)

    @staticmethod
    def get_teams():
        f = open("./class/teams.json")
        teams = json.load(f)
        return teams

    # Params:
    #   hub: PyGitHub github object
    #   org: PyGitHub organization object
    # Purpose:
    #   To iterate over all the GitHub IDs in a class.txt file
    #   and add the GitHub users to the organization's membership.
    # N.B.: class.txt is a text file with student gitIDs on each line
    def set_members(self):
        class_list = open("./class/class.txt", "r")
        c = [line.strip() for line in c]
        class_list.close()

        for student in c:
            self.org.add_to_public_members(self.hub.get_user(student))

    # Default: Each student in the class is in their own team
    # Nondefault:   If students are allowed to form groups, then their groups should
    #               be identified in teams.txt
    # Should check that students are not member of more than one group.
    # class.txt is a text file with student gitIDs on each line
    # teams.txt is a text file that identifies which student gitIDs are proposed
    # to be group members.  Groups are separated by the term "team:".
    # team:
    # <member>
    # <member>
    # team:
    # <member>
    @staticmethod
    def set_teams():
        print "Parsing class & team files."
        teams = {}
        class_list = open("./class/class.txt", "r")
        teams_list = open("./class/teams.txt", "r")
        t = teams_list.readlines()
        c = class_list.readlines()
        t = [line.strip() for line in t]
        c = [line.strip() for line in c]
        i = 0
        class_list.close()
        teams_list.close()

        for line in c:
            line = line.strip()
            if line in t:
                pass    # Skip over students in groups
            else:
                team_name = "team" + str(i)
                teams[team_name] = [line]
                i += 1
        for j in range(len(t)):
            team_name = "team" + str(i)
            team = []
            if t[j] == "team:":
                j += 1
                while t[j] != "team:":
                    team.append(t[j])
                    j += 1
                    if j == len(t):
                        break
                teams[team_name] = team
                i += 1

        out = open("./class/team_defs.json", "w")
        json.dump(teams, out)
        out.close()

    # Params:
    #   hub: PyGitHub github object
    #   org: PyGitHub organization object
    # Purpose:
    #   To iterate over all the teams defined locally with ten_defs.json
    #   and create teams on GitHub.
    def set_git_teams(self):
        print "Setting teams on GitHub."

        f = open("./class/team_defs.json", "r")
        teams = json.load(f)
        f.close()

        for team in teams.keys():
            t = None
            try:
                t = self.org.create_team(team)
                print "Created " + team + " on GitHub."
            except:
                print "Error creating team: team {} already exists.".format(team)
            for member in teams[team]:
                t.add_to_members(self.hub.get_user(member))
    
    # Param:
    #   org: PyGitHub organization object
    #   lab: string identifier for the base code for a lab.  Defaults to testlab1.
    # Purpose:
    #   To iterate over all the teams for the CMPUT229 GitHub organization and
    #   assign each team a clone of the repo containing the base code.
    def set_repos(self, lab="testlab1"):
        print "Setting repos."
        teams = self.org.get_teams()

        repos = {}
        try:
            print "Setting local clone of base code."
            base, url = self.local_clone(lab)
            repos["instructor"] = {lab: url}
        except Exception as e:
            print "Error making local clone of base code."
            print e
            return

        for team in teams:
            if team.name != "Students":
                try:
                    print "Assigning " + team.name + " the repo."
                    team_repo = self.clone(lab, team, base) 
                    repos[team.name] = team_repo
                except Exception as e:
                    print "Error cloning lab for " + team.name
                    print e
                    time.sleep(5)
                    print "Waiting before trying again."
                    try:
                        print "Assigning " + team.name + " the repo."
                        team_repo = self.clone(lab, team, base) 
                        repos[team.name] = team_repo
                    except Exception as e:
                        print "Error cloning lab for " + team.name
                        print e
                        
        self.remove_local()
        f = open("./class/teams.json", "w")
        json.dump(repos, f)
        f.close()

    # Param:
    #   org: PyGitHub organization object
    #   lab: string identifier for a lab.  Defaults to testlab1.
    # Purpose:
    #   Iterates over all repos for all teams in the organization and 
    #   deletes each team's repo for a given lab.
    def del_repos(self, lab="testlab1"):
        teams = self.org.get_teams()
        for team in teams:
            repos = team.get_repos()
            for repo in repos:
                if lab in repo.name:
                    print "Deleting repo " + repo.name
                    repo.delete()

    # Param:
    #   org: PyGitHub organization object
    # Iterates over all teams in the organization & deletes them.
    def del_teams(self):
        teams = self.org.get_teams()
        for team in teams:
            if team.name != "Students":
                members = team.get_members()
                for member in members:
                    team.remove_from_members(member)
                print "Deleting team " + team.name
                team.delete()

    # Params:
    #   lab: identifier for the lab, eg "lab1".
    #   team: PyGitHub team object.
    #   base_repo: GitPython repo object.
    #   org: PyGitHub organization object
    # Purpose:
    #   Distributes the repo to a team from a local copy of the repo.
    # Returns:
    #   A dictionary mapping the lab identifier to the url of the team's clone.
    def clone(self, lab, team, base_repo):
        base_url = self.url+lab
        repo_name = "{}_{}".format(lab, team.name)
        repo_url = self.url + repo_name
        team_repo = self.org.create_repo(repo_name, team_id=team)
        remote = base_repo.create_remote(team_repo.name, self.insert_auth(repo_url))
        remote.push()  
        return {lab: repo_url}

    # Param:
    #   lab: string identifier for a lab
    # Purpose:
    #   Creates a local copy of the lab's base code in order to distribute it to students in the class.
    # Return:
    #   GitPython Repo object
    def local_clone(self, lab):
        token = self.get_token()
        url = self.url+lab
        base_repo = Repo.clone_from(self.insert_auth(url), "./base/")
        return base_repo, url

    # Removes the local copy of the repo after distribution 
    def remove_local(self):
        shutil.rmtree("./base/")

    # Param:
    #   url: string representation of a GitHub resource.
    # Purpose:
    #   Inserts an oauth token in the url to make access easier, and to keep from committing 
    #   oauth tokens to git repos.  It lets the url remain unaltered at the higher scope.
    #   Needed for access using GitPython (different interface from PyGitHub).
    # Returns:
    #   The url, but with oauth token inserted
    def insert_auth(self, url):
        token = self.get_token()
        url = url[:url.find("://")+3] + token + ":x-oauth-basic@" + url[url.find("github"):]
        return url

# Steps through team formation, repo assignment, repo deletion, and team deletion
def main():
    org_name = "GitHubClassroomTestCMPUT229"
    m = Manager(org_name)
    # m.set_teams()
    # m.set_git_teams()
    m.set_repos("testlab1")
    # raw_input("TEAMS & REPOS MADE. AWAITING INPUT TO PROCEED.")
    # del_repos(org)
    # del_teams(org)
    return

if __name__ == "__main__":
    main()

