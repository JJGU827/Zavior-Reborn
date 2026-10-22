# Zavior Discord Bot Starter

1. Create a virtual environment: `python3 -m venv .venv`
2. Activate it: `source .venv/bin/activate` (Windows: `.venv\\Scripts\\Activate.ps1`)
3. Install packages: `python -m pip install -r requirements.txt`
4. Copy `.env.example` to `.env`, then add your bot token and optional test server ID.
5. Run: `python bot.py`

Invite the bot with the `bot` and `applications.commands` scopes. Enable the appropriate permissions to send messages. The `/suggest` command only validates links; it does not save recommendations yet.
