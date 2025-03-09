import requests
import time

def submit_bol_to_mindee(file, api_key):
    """
    Submits a file to the Mindee API asynchronously and returns the job ID and polling URL.

    Args:
        file: The uploaded file object.
        api_key (str): The Mindee API key.

    Returns:
        tuple: (job_id, polling_url)
    """
    url = "https://api.mindee.net/v1/products/mindee/bill_of_lading/v1/predict_async"
    headers = {"Authorization": f"Token {api_key}"}
    files = {"document": file}

    response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()

    job_response = response.json()
    job_id = job_response["job"]["id"]
    
    # Construct the correct polling URL
    polling_url = f"https://api.mindee.net/v1/products/mindee/bill_of_lading/v1/jobs/{job_id}"
    
    return job_id, polling_url

def get_bol_result(api_key, polling_url):
    """
    Polls the Mindee API until the job is completed.

    Args:
        api_key (str): The Mindee API key.
        polling_url (str): The URL to poll for job status.

    Returns:
        dict: The parsed document data.
    """
    headers = {"Authorization": f"Token {api_key}"}
    
    while True:
        response = requests.get(polling_url, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        status = result.get("job", {}).get("status")
        if status == "completed":
            return result.get("document", {})  # Adjust based on actual response structure
        elif status in ["failed", "error"]:
            raise Exception(f"Job failed with status: {status}")
        
        time.sleep(2)  # Poll every 2 seconds

# Example usage in your app (e.g., Streamlit)
import streamlit as st

st.title("Bill of Lading Parser")
uploaded_file = st.file_uploader("Upload a BoL", type=["pdf", "jpg", "png"])

if uploaded_file:
    api_key = "your_api_key_here"  # Replace with your actual key
    job_id, polling_url = submit_bol_to_mindee(uploaded_file, api_key)
    st.write(f"Waiting for job {job_id} to complete at {polling_url}...")
    result = get_bol_result(api_key, polling_url)
    st.json(result)