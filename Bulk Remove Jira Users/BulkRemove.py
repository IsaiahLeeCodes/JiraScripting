import argparse
import base64
import csv
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List

import requests

ADMIN_API_BASE = os.getenv("ATLASSIAN_ADMIN_API_BASE", "https://api.atlassian.com/admin/v1")

# --- Configuration: plug-in your values here ---
ATLASSIAN_EMAIL = "johndoe@email.com" #Replace with the email of an admin user on the Jira site. Can also be set via ATLASSIAN_EMAIL environment variable.
ATLASSIAN_API_TOKEN = "API_TOKEN_HERE" #Replace with an API token generated for the admin user. Can also be set via ATLASSIAN_API_TOKEN environment variable.
ATLASSIAN_SITE_URL = "https://your-org.atlassian.net"  # Replace with your Jira site URL
CSV_FILE = "users.csv"
LOG_FILE = ""
# ---------------------------------------------


def get_auth_headers() -> Dict[str, str]:
    email = os.getenv("ATLASSIAN_EMAIL") or ATLASSIAN_EMAIL
    api_token = os.getenv("ATLASSIAN_API_TOKEN") or ATLASSIAN_API_TOKEN
    if email and api_token:
        credentials = f"{email}:{api_token}".encode("utf-8")
        encoded = base64.b64encode(credentials).decode("utf-8")
        return {"Authorization": f"Basic {encoded}"}

    raise SystemExit(
        "Missing authentication configuration. Set ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove Jira access for one or more Atlassian users by removing them from the jira-software-users group."
    )
    parser.add_argument(
        "--account-id",
        help="Single Atlassian accountId of the user to remove Jira access from.",
    )
    parser.add_argument(
        "--csv-file",
        help="CSV file containing one accountId per row or a header named accountId. Falls back to CSV_FILE if set.",
    )
    parser.add_argument(
        "--log-file",
        help="Path to write execution logs. Defaults to BulkRemove_<timestamp>.log in the current directory.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode to print request details (without sensitive data).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making any changes.",
    )
    return parser.parse_args()


def load_account_ids_from_csv(file_path: str) -> List[str]:
    account_ids: List[str] = []
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        if "accountId" in reader.fieldnames:
            for row in reader:
                value = row.get("accountId")
                if value:
                    account_ids.append(value.strip())
        else:
            csvfile.seek(0)
            reader = csv.reader(csvfile)
            for row in reader:
                if row:
                    account_ids.append(row[0].strip())
    return [value for value in account_ids if value]


def setup_logger(log_file: str) -> logging.Logger:
    logger = logging.getLogger("bulk_remove_jira_access")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def remove_jira_access(
    site_url: str,
    account_id: str,
    groupname: str,
    headers: Dict[str, str],
    logger: logging.Logger,
    debug: bool = False,
) -> bool:
    endpoint = f"{site_url}/rest/api/3/group/user"
    params = {"groupname": groupname, "accountId": account_id}

    if debug:
        logger.info("DEBUG: Endpoint: %s", endpoint)
        logger.info("DEBUG: Params: %s", params)
        logger.info("DEBUG: Headers: %s", {k: "***masked***" if k.lower() == "authorization" else v for k, v in headers.items()})
        logger.info("DEBUG: Full URL: %s?%s", endpoint, "&".join(f"{k}={v}" for k, v in params.items()))

    response = requests.delete(endpoint, headers=headers, params=params, timeout=30)

    if response.status_code == 200:
        logger.info("Removed Jira access for accountId=%s from group '%s' on site", account_id, groupname)
        return True

    try:
        error_text = response.json()
    except ValueError:
        error_text = response.text

    if response.status_code == 401:
        logger.error(
            "Unauthorized (401) for accountId=%s in group '%s'. Check that the email and API token are valid and you have site admin permissions.",
            account_id,
            groupname,
        )
    elif response.status_code == 404:
        logger.error(
            "User not found (404) for accountId=%s in group '%s'. User may not be in this group or accountId is invalid.",
            account_id,
            groupname,
        )
    logger.error(
        "Failed to remove Jira access for accountId=%s from group '%s'. Status=%s, response=%s",
        account_id,
        groupname,
        response.status_code,
        error_text,
    )
    return False


def main() -> None:
    args = parse_args()
    site_url = ATLASSIAN_SITE_URL
    if not site_url or site_url == "https://your-org.atlassian.net":
        raise SystemExit("Please set ATLASSIAN_SITE_URL to your Jira site URL.")

    headers = get_auth_headers()
    log_file = (args.log_file if args and hasattr(args, 'log_file') else None) or LOG_FILE or f"BulkRemove_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.log"
    logger = setup_logger(log_file)
    logger.info("Using Basic authentication for Jira REST API")
    logger.info("Site URL: %s", site_url)

    account_ids: List[str] = []
    if args and hasattr(args, 'account_id') and args.account_id:
        account_ids.append(args.account_id.strip())

    csv_path = (args.csv_file if args and hasattr(args, 'csv_file') else None) or CSV_FILE
    if csv_path:
        if not os.path.exists(csv_path):
            logger.error("CSV file not found: %s", csv_path)
            raise SystemExit(f"CSV file not found: {csv_path}")
        csv_ids = load_account_ids_from_csv(csv_path)
        account_ids.extend(csv_ids)

    if not account_ids:
        logger.error("No accountId values provided.")
        raise SystemExit("Provide --account-id or --csv-file with at least one accountId.")

    account_ids = [value for value in account_ids if value]
    unique_ids = list(dict.fromkeys(account_ids))

    dry_run = args and hasattr(args, 'dry_run') and args.dry_run
    if dry_run:
        logger.info("Dry run mode enabled. The following accountIds would be processed:")
        groups = ["jira-software-users", "jira-users"]
        for account_id in unique_ids:
            for group in groups:
                logger.info(" - Remove %s from group '%s'", account_id, group)
        return

    logger.info(
        "Removing Jira access for %d account(s) from site...",
        len(unique_ids),
    )
    successes = 0
    total_operations = 0
    debug = args and hasattr(args, 'debug') and args.debug
    groups = ["jira-software-users", "jira-users"] #can be edited to choose what groups to remove users from, but these are the default groups that grant Jira access. Removing from both ensures access is removed regardless of which group they were in. 
    for account_id in unique_ids:
        for group in groups:
            total_operations += 1
            if remove_jira_access(site_url, account_id, group, headers, logger, debug):
                successes += 1

    logger.info("Finished: %d/%d removals succeeded.", successes, total_operations)
    logger.info("Execution log written to %s", log_file)


if __name__ == "__main__":
    main()
