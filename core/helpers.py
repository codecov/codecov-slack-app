service_mapping = {
    "gh": "github",
    "github": "github",
    "bb": "bitbucket",
    "bitbucket": "bitbucket",
    "gl": "gitlab",
    "gitlab": "gitlab",
}


def validate_owner_params(owner_username, service, say):
    if not owner_username or not service:
        raise ValueError("Please provide a username and service")
    normalized_name = service_mapping.get(service.lower())
    if normalized_name is None:
        raise ValueError(
            "Invalid service. valid services are: github, bitbucket, gitlab"
        )

    return normalized_name


def extract_command_params(command_text):
    params_dict = {}

    for command in command_text:
        if "=" not in command:
            continue

        params_dict[command.split("=")[0]] = command.split("=")[1]

    return params_dict

def extract_users_optional_params(params_dict):
    activated = params_dict.get("activated")
    is_admin = params_dict.get("is_admin")
    search = params_dict.get("search")
    page = params_dict.get("page")
    page_size = params_dict.get("page_size")

    optional_params = {}
    if activated:
        optional_params["activated"] = activated
    if is_admin:
        optional_params["is_admin"] = is_admin
    if search:
        optional_params["search"] = search
    if page:
        optional_params["page"] = page
    if page_size:
        optional_params["page_size"] = page_size

    return optional_params