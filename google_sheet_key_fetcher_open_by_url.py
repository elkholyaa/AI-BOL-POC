"""
File: google_sheet_key_fetcher_open_by_url.py

Purpose:
    Demonstrates how to read an API key from a private Google Sheet using a
    service account and open_by_url(). This ensures you're connecting to the
    exact sheet, even if its name or ordering changes.

Role & Integration:
    - Uses the Google Sheets API via gspread and google-auth libraries.
    - Retrieves an API key from a specified cell (A1 by default).
    - Provides debug info for diagnosing why a different value might appear.

Workflow:
    1. You have a Google Sheet that stores your API key in cell A1.
    2. You share the sheet with your service account's email (Editor or Viewer).
    3. You use open_by_url() with the exact sheet URL to avoid referencing the wrong sheet.
    4. This script prints all rows and the value in cell A1.

Usage Instructions:
    1. pip install gspread google-auth
    2. Save your service account JSON file as 'service_account_credentials.json'
       in the same directory as this file.
    3. Update SHEET_URL below with your Google Sheet URL.
    4. Run:
         python google_sheet_key_fetcher_open_by_url.py

Security Tips:
    - Keep your JSON credentials file private. Do not commit it to public repos.
    - Restrict access to your Google Sheet to only the service account and trusted collaborators.
"""

import gspread
from google.oauth2.service_account import Credentials

# Replace with your actual sheet URL:
SHEET_URL = "https://docs.google.com/spreadsheets/d/12YB3_xHh0ngsh1gwQADC1vpqQFgjuX4x-VvLoD8_7R0/edit#gid=0"

CELL_ADDRESS = "A1"  # The cell that should contain your API key.

def get_api_key_from_sheet(json_file="service_account_credentials.json"):
    """
    Reads the API key from a private Google Sheet using open_by_url().
    
    :param json_file: Path to the service account JSON credentials file.
    :return: The string stored in cell A1 (by default).
    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(json_file, scopes=scope)
    client = gspread.authorize(creds)

    # Open the sheet by URL (this is the most reliable method).
    doc = client.open_by_url(SHEET_URL)

    # List all worksheets (tabs) for debugging:
    worksheets = doc.worksheets()
    print("Debug: Available worksheets/tabs:")
    for ws in worksheets:
        print(f" - Title: {ws.title}")

    # Get the first worksheet (index 0) or specify by name if needed.
    sheet = doc.get_worksheet(0)
    print(f"Debug: Using worksheet: {sheet.title}")

    # Print all rows for debugging:
    all_values = sheet.get_all_values()
    print("Debug: All rows in this worksheet:")
    for row in all_values:
        print(row)

    # Retrieve the specified cell (A1) and debug:
    cell = sheet.acell(CELL_ADDRESS)
    print(f"Debug: Raw cell object for A1: {cell}")
    print(f"Debug: Cell A1 value: {cell.value}")

    return cell.value

def main():
    try:
        key = get_api_key_from_sheet()
        if not key:
            print("No API key found in cell A1.")
        else:
            print(f"Retrieved API key: {key}")
    except Exception as e:
        print("Error retrieving API key from Google Sheet:")
        print(str(e))

if __name__ == "__main__":
    main()
