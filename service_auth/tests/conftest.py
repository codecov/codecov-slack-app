import os

os.environ["CODECOV_PUBLIC_API"] = "https://codecov.io/api"
os.environ["GITHUB_CLIENT_ID"] = "test_client_id"
os.environ["GITHUB_CLIENT_SECRET"] = "test_client_secret"
os.environ["GITHUB_REDIRECT_URI"] = "http://test/auth/github/callback"
os.environ["USER_ID_SECRET"] = "test_user_id_secret"
os.environ["SLACK_CLIENT_ID"] = "292929292929.292929292929"
os.environ["SLACK_CLIENT_SECRET"] = "random_client_secret"
os.environ["SLACK_APP_ID"] = "292929292929"