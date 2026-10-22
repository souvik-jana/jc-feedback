# jc-feedback

Printable anonymous feedback sheet and Google Form for the GW journal club.

1. **Install:** `uv sync`
2. **Each JC:** `uv run jc make --title "Paper title" --date YYYY-MM-DD`. Print `out/<date>/JC_feedback_<date>.pdf`. The QR code is also in that folder.
3. **Edit questions or labels:** change `config.yaml`, then run `uv run jc sync --dry-run`, then `uv run jc sync`, then `uv run jc check`. Keep each question's `key`, so its past answers stay in the same column.
4. **New organiser, one-time setup:** ask the form owner for *editor* access to the Google Form. Then, in Google Cloud Console, create a project, enable the **Google Forms API**, set the OAuth consent screen to External/Testing with yourself as a test user, and create a **Desktop app** client. Save its JSON as `credentials.json` here.
5. **Never commit `credentials.json` or `token.json`.** Both are in `.gitignore`. To revoke access, go to https://myaccount.google.com/permissions.
