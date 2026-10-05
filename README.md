# attendance

Telegram bot for marking attendance in Google Sheets based on a Zoom Participants screenshot.

Bot: @zoom_attendance_helper_bot  
Admin access: email smmaximss@gmail.com

## Setup

1) Create `.env` from `.env.example` and fill required values:
- BOT_TOKEN
- OPENAI_API_KEY
- GOOGLE_SERVICE_ACCOUNT_FILE
- WORKSHEET_NAME
- ROSTER_NAME_COL
- ROSTER_START_ROW

2) Put the Google Service Account JSON at `./secrets/service_account.json`

3) Share the target Google Sheet with the service account email as Editor.

## Run

```bash
python -m attendance
```

## Commands
- /start
- /sheet
- /sheet ID-or-URL
- /help
- /cancel