# Automatic Google Meet links

The CRM creates real Google Meet rooms through the Google Calendar API. Random
`meet.google.com` codes are not valid.

## Personal Gmail or Google Workspace OAuth

Enable the Google Calendar API in a Google Cloud project, create an OAuth client,
and obtain a refresh token authorized with this scope:

`https://www.googleapis.com/auth/calendar`

Add these values to `backend/.env`:

```dotenv
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REFRESH_TOKEN=your-refresh-token
GOOGLE_CALENDAR_ID=primary
```

Restart Django after changing `.env`. New online meetings will then create a
Calendar event with a real Google Meet link automatically.

## Google Workspace service account

For a Workspace domain, domain-wide delegation can be used instead:

```dotenv
GOOGLE_SERVICE_ACCOUNT_FILE=C:/absolute/path/service-account.json
GOOGLE_IMPERSONATE_USER=calendar-owner@your-domain.com
GOOGLE_CALENDAR_ID=primary
```

The Workspace administrator must authorize the service account for the Calendar
scope shown above. Keep credential files and secrets out of source control.
