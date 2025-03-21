"""
File: google_sheet_key_fetcher.py

Purpose:
    This script demonstrates how to read an API key from a private Google Sheet using a
    service account. It authenticates with a JSON credentials file and retrieves the key
    stored in a specified cell (default is A1) of the first worksheet.
    
Role & Integration:
    - Uses the Google Sheets API via gspread and google-auth libraries.
    - The API key (for example, for Mindee) is stored in a private Google Sheet.
    - This approach helps you manage the key securely without hardcoding it in your code.
    
Workflow:
    1. Create a Google Sheet (e.g., named "API Keys") and store your API key in cell A1.
    2. Create a service account in Google Cloud Console, enable the Google Sheets API,
       and download the JSON credentials file (e.g., "service_account_credentials.json").
    3. Share the Google Sheet with the service account’s email.
    4. Run this script to retrieve and print the API key.
    
Usage Instructions:
    1. Install dependencies:
         pip install gspread google-auth
    2. Place "service_account_credentials.json" in the same directory as this file.
    3. Ensure your Google Sheet (named "API Keys" by default) has your API key in cell A1.
    4. Run:
         python google_sheet_key_fetcher.py

Security Tips:
    - Keep the JSON credentials file private. Do not commit it to a public repository.
    - Restrict access to your Google Sheet to only the service account and trusted collaborators.
"""

import gspread
from google.oauth2.service_account import Credentials

# Define the Google Sheet details
SHEET_NAME = "API Keys"  # Change if your sheet has a different name.
CELL_ADDRESS = "A1"      # The cell where the API key should be stored.

def get_api_key_from_sheet(json_file="service_account_credentials.json"):
    """
    Reads the API key from a private Google Sheet.
    
    :param json_file: Path to the service account JSON credentials file.
    :return: The API key as a string, retrieved from the specified cell.
    """
    # Define the scopes required to access Google Sheets and Drive.
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Authenticate using the service account credentials.
    creds = Credentials.from_service_account_file(json_file, scopes=scope)
    client = gspread.authorize(creds)
    
    # Open the sheet by name and select the first worksheet.
    sheet = client.open(SHEET_NAME).sheet1
    
    # For debugging: print all values in the sheet
    all_values = sheet.get_all_values()
    print("Debug: All values in the sheet:")
    for row in all_values:
        print(row)
    
    # Retrieve the specified cell and print debug information.
    cell = sheet.acell(CELL_ADDRESS)
    print(f"Debug: type(cell): {type(cell)}")
    print(f"Debug: Raw cell {CELL_ADDRESS} content: {cell}")
    print(f"Debug: Cell {CELL_ADDRESS} value: {cell.value}")
    
    # Return the value from the cell.
    api_key = cell.value
    return api_key

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
