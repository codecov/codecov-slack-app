service_mapping = {
    'gh': 'github',
    'github': 'github',
    'bb': 'bitbucket',
    'bitbucket': 'bitbucket',
    'gl': 'gitlab',
    'gitlab': 'gitlab',
}

def validate_owner_params(owner_username, service, say):
    if not owner_username or not service:
        raise ValueError("Please provide a username and service")
    normalized_name = service_mapping.get(service.lower())
    if normalized_name is None:
        raise ValueError("Invalid service. valid services are: github, bitbucket, gitlab")

