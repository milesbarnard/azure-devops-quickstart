class GitRepo:
    def __init__(self, full_name, url, default_branch, is_fork, repo_id):
        self.full_name = full_name
        self.url = url
        self.default_branch = default_branch
        self.is_fork = is_fork
        self.repo_id = repo_id

