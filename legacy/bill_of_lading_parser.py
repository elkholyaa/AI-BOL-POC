# bill_of_lading_parser.py
"""
Purpose:
    This script is a proof-of-concept (POC) for the AI-BOL-POC application that parses a
    Bill of Lading document using Mindee's asynchronous API via the Python SDK.
    
Role and Integration:
    - This file is part of the AI-BOL-POC repository.
    - It uses the Mindee Python SDK to submit a Bill of Lading PDF for parsing and retrieves
      the parsed JSON data.
    - It specifically interfaces with Mindee's BillOfLadingV1 product.
    
Workflow:
    1. Initialize the Mindee client with your API key.
    2. Load the PDF file ("medu2.pdf") from the current directory.
    3. Enqueue the document for asynchronous parsing; the SDK will poll until the job is complete.
    4. Print the resulting JSON output containing the parsed document data.
    
Installation and Setup:
    - Ensure you have Python 3.x installed.
    - Install the Mindee Python SDK by running:
          pip install mindee
    - If you see the error "Import 'mindee' could not be resolved" (as reported by Pylance),
      it means that either the Mindee package is not installed in your current environment or
      VSCode is not using the correct interpreter.
        • In VSCode, verify your selected Python interpreter (bottom-left or via the Command Palette)
          and ensure it points to the environment where 'mindee' is installed.
    
Usage Instructions:
    1. Save this file as bill_of_lading_parser.py in your project folder (e.g., F:\projects\AI-BOL-POC).
    2. Ensure that the file "medu2.pdf" is located in the same directory as this script.
    3. Open Git Bash (or another terminal), navigate to your project folder, and run:
          python bill_of_lading_parser.py
          
Educational Notes:
    - The method `enqueue_and_parse` is used to handle asynchronous processing. It enqueues the document
      and polls the API until the job is complete, then returns the parsed data.
    - The output printed is a JSON representation of the parsed Bill of Lading data.
"""

from mindee import Client, product, AsyncPredictResponse

def main():
    # Initialize the Mindee client with your API key.
    # Replace with your actual API key if necessary.
    mindee_client = Client(api_key="f2a2667c4360e3532d1c43f73b1a5827")
    
    # Define the path to the Bill of Lading PDF file.
    # Here, we assume the file is named "medu2.pdf" and is located in the current directory.
    pdf_path = "./medu2.pdf"
    
    # Load the PDF file using the client's helper function.
    input_doc = mindee_client.source_from_path(pdf_path)
    
    # Enqueue the document for asynchronous parsing using the BillOfLadingV1 endpoint.
    # The enqueue_and_parse method handles the polling until the job is complete.
    result: AsyncPredictResponse = mindee_client.enqueue_and_parse(
        product.BillOfLadingV1,
        input_doc,
    )
    
    # Print the JSON output of the parsed document.
    print(result.document)

if __name__ == "__main__":
    main()
