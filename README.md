# attendance

Telegram bot for marking attendance in Google Sheets based on a Zoom Participants screenshot.

Bot: @AttendoraBot  
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

Excel files (.xlsx) kept in Google Drive work too: the bot downloads the file, sets the marks
and uploads it back. That needs the Google Drive API enabled next to the Sheets API, and
images or charts inside such a file do not survive the round trip.

## Run

```bash
python -m attendance
```

## Deployment

The bot runs on `main` as the `attendance` component of infra: long polling, no ports.
On apply, `integration/deploy.py` takes the `attendance` object from SOPS, renders `.env`
and the service account file, and starts the container. The user → sheet database lives
in `runtime/` and survives redeploys.

| SOPS key | Value |
| --- | --- |
| `bot_token` | Telegram bot token |
| `openai_api_key` | OpenAI API key |
| `openai_base_url` | Optional, `https://openrouter.ai/api/v1` to go through OpenRouter |
| `google_service_account` | Service account JSON key, pasted as an object |
| `worksheet_name`, `roster_name_col`, `roster_start_row` | Roster location, as in `.env` |
| `default_sheet_id` | Optional default spreadsheet |
| `present_mark`, `absent_mark` | Optional marks for present and absent students: `1` and none by default, `П` and `Н` for a sheet that counts those |
| `openai_model` | Optional, `gpt-6-luna` by default (`openai/gpt-6-luna` on OpenRouter) |
| `admin_ids` | Optional comma-separated Telegram IDs; without it the bot answers everyone |

## Commands
- /start
- /sheet
- /sheet ID-or-URL
- /help
- /cancel