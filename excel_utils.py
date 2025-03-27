# excel_utils.py
"""
Purpose:
  This file provides utility functions for Excel file manipulation within the AI-BOL-POC application.
  Specifically, it contains a function to append a row to an existing Excel file (default "bol.xlsx").

Role:
  - Supports the proof-of-concept by enabling the addition of new rows (e.g., Bill of Lading data) to an Excel file.
  - Can be imported into other parts of the application where Excel updates are needed.

Overview:
  - The function attempts to read the existing Excel file into a DataFrame.
  - If the file does not exist, it creates an empty DataFrame.
  - The new row (provided as a dictionary) is then appended and the updated DataFrame is written back to the file.
"""

import pandas as pd

def append_row_to_excel(row_data, file_path="bol.xlsx"):
    """
    Appends a new row of data to the specified Excel file.

    Parameters:
      row_data (dict): A dictionary where keys are column names and values are the data to append.
      file_path (str): The path to the Excel file to update. Defaults to "bol.xlsx".

    Workflow:
      - Attempts to read the existing Excel file into a DataFrame.
      - If the file does not exist, creates an empty DataFrame.
      - Appends the new row to the DataFrame.
      - Writes the updated DataFrame back to the Excel file.
    """
    try:
        # Attempt to read the existing Excel file.
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        # If the file doesn't exist, create an empty DataFrame.
        df = pd.DataFrame()

    # Convert the row_data dictionary into a DataFrame (single row).
    new_row = pd.DataFrame([row_data])
    
    # Append the new row to the DataFrame.
    df = pd.concat([df, new_row], ignore_index=True)
    
    # Save the updated DataFrame back to the Excel file.
    df.to_excel(file_path, index=False)

# Test the function if this file is executed directly.
if __name__ == "__main__":
    sample_row = {
        "Bill of Lading No.": "MSCUKK871206",
        "Shipper": "ABC Shipping",
        "Consignee": "XYZ Importers",
        "Port of Loading": "Port A",
        "Port of Discharge": "Port B"
    }
    append_row_to_excel(sample_row)
