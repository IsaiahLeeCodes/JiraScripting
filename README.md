# JiraScripting

Quick scripts to perform updates in Jira.

## Bulk Remove Jira Users

This repository contains a Python script that removes Jira access for one or more Atlassian users by removing them from the `jira-software-users` and `jira-users` groups.

## Dependencies

- Python 3.8 or newer
- `requests` library

Install dependencies with:

```powershell
python -m pip install requests
```

## Configuration

The script uses the following configuration values, which can be set either by editing `Bulk Remove Jira Users/BulkRemove.py` or by exporting environment variables.

- `ATLASSIAN_EMAIL`: Atlassian admin user email
- `ATLASSIAN_API_TOKEN`: Atlassian API token for the admin user
- `ATLASSIAN_SITE_URL`: Jira site URL (for example `https://your-org.atlassian.net`)
- `ATLASSIAN_ADMIN_API_BASE`: Optional base URL for the Atlassian Admin API. Defaults to `https://api.atlassian.com/admin/v1`

Example environment setup:

```powershell
$env:ATLASSIAN_EMAIL = 'admin@example.com'
$env:ATLASSIAN_API_TOKEN = 'your_api_token_here'
$env:ATLASSIAN_SITE_URL = 'https://your-org.atlassian.net'
```

## Usage

Run the script with a single `accountId`:

```powershell
python "Bulk Remove Jira Users/BulkRemove.py" --account-id 123456:abcd-efgh-ijkl
```

Or provide a CSV file with one `accountId` per row or a header named `accountId`:

```powershell
python "Bulk Remove Jira Users/BulkRemove.py" --csv-file users.csv
```

You can also enable debugging or generate a custom log file:

```powershell
python "Bulk Remove Jira Users/BulkRemove.py" --csv-file users.csv --debug --log-file remove.log
```

Use dry-run mode to preview changes without deleting any group memberships:

```powershell
python "Bulk Remove Jira Users/BulkRemove.py" --csv-file users.csv --dry-run
```

## CSV Format

The CSV file may be either:

- A single column containing account IDs
- A header row with `accountId`

Example 1:

```csv
123456:abcd-efgh-ijkl
789012:mnop-qrst-uvwx
```

Example 2:

```csv
accountId
123456:abcd-efgh-ijkl
789012:mnop-qrst-uvwx
```

## Notes

- The script removes users from the Jira groups `jira-software-users` and `jira-users`. Editable from: Line 199
- If no `accountId` values are provided, the script will exit with an error.
- The script writes execution logs to a timestamped file by default.
