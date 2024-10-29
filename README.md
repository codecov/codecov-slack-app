# Codecov Slack App 
Codecov Slack App Implementation for a Slack app intended to serve Codecov customers by using Codecov public API.

#  Running the app locally

1. Create a virtual environment in the root directory of the app:
   ```
   python3 -m venv venv
   ```

2. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```

3. Install the required dependencies using pip:
   ```
   pip install -r requirements.txt
   ```

4. Install Docker:
   Make sure you have Docker installed. If you do not have Docker installed, please refer to the Docker documentation to install it on your local machine.

5. Start the Docker containers:
   ```
   make up
   ```
   (For the first run, `make gcr.login` may be needed.)

6. Set up ngrok as a local proxy:
   - Install and configure ngrok to expose a public endpoint that Slack can use to send your app events. Run the following command:
     ```
     ngrok http 8000
     ```
     Refer to [this link](https://api.slack.com/start/building/bolt-python#ngrok) to learn more about using ngrok.

7. Create a Slack app:
   - Go to [https://api.slack.com/apps?new_app=1&ref=bolt_start_hub](https://api.slack.com/apps?new_app=1&ref=bolt_start_hub) to create a new app in the Slack API. Follow the instructions provided in the link.

8. Configure environment variables:
   - Create an `.env` file in your local environment and copy the required tokens into it. Your `.env` file should look like this:
     ```
     # DB Settings
     SQL_ENGINE=django.db.backends.postgresql
     POSTGRES_DB=db
     POSTGRES_USER=db
     POSTGRES_PASSWORD=password
     SQL_HOST=db
     SQL_PORT=5432

     # Django Settings
     DJANGO_SETTINGS_MODULE=codecov_slack_app.settings
     DJANGO_SECRET_KEY=secret

     # Slack App Settings
     SLACK_CLIENT_ID=
     SLACK_CLIENT_SECRET=
     SLACK_SIGNING_SECRET=
     SLACK_SCOPES=chat:write,commands,users:read,users:read.email,app_mentions:read,channels:join,channels:read,files:write,groups:read,im:read,mpim:read
     SLACK_REDIRECT_URI=YOUR_NGROK_TUNNEL/slack/oauth_redirect
     SLACK_APP_ID=

     # GitHub Slack App Settings (You'll need this if you care to test GitHub app locally)
     GITHUB_APP_ID=
     GITHUB_CLIENT_ID=
     GITHUB_CLIENT_SECRET=
     GITHUB_REDIRECT_URI=NGROK_TUNNEL_URL/auth/gh/callback

     # CODECOV env variables
     CODECOV_INTERNAL_TOKEN=
     CODECOV_PUBLIC_API=https://stage-api.codecov.dev/api/v2
     CODECOV_API_URL=https://stage-api.codecov.dev

     USER_ID_SECRET=random_secret
     SENTRY_ENVIRONMENT=staging

     RUN_ENV=LOCAL
     ```

9. Update request URLs in the Slack app dashboard:
   - Update the request URL in multiple areas of the Slack app dashboard with the ngrok tunnel you've created:
     - Use `NGROK_TUNNEL_URL/slack/events` in [https://api.slack.com/apps/YOUR_APP_ID/interactive-messages](https://api.slack.com/apps/YOUR_APP_ID/interactive-messages)
     - Use `NGROK_TUNNEL_URL/slack/events` after enabling events in [https://api.slack.com/apps/YOUR_APP_ID/event-subscriptions](https://api.slack.com/apps/YOUR_APP_ID/event-subscriptions)
     - Create a command called `/codecov` in [https://api.slack.com/apps/YOUR_APP_ID/slash-commands](https://api.slack.com/apps/YOUR_APP_ID/slash-commands) and append the request URL to it
     - Use `NGROK_TUNNEL_URL/slack/auth_redirect` in the redirect URLs in [https://api.slack.com/apps/YOUR_APP_ID/oauth](https://api.slack.com/apps/YOUR_APP_ID/oauth)

10. Installation:
    - Visit `NGROK_TUNNEL_URL/slack/install`. You should see the Slack installation page. Follow the instructions to install the app.
   


That's it! 🎉 Your Slack app should now be set up and running locally.

ℹ️ Please note that you need to replace `YOUR_APP_ID` and `NGROK_TUNNEL_URL` with the appropriate values for your application.
