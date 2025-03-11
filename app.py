import streamlit as st
import gspread
import json
import os
import tempfile
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from mindee import Client, product, AsyncPredictResponse

# Hide Streamlit UI elements
hide_streamlit_style = """
<style>
.viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_, 
.viewerBadge_link__1S137, .viewerBadge_text__1JaDK {
    display: none !important;
}
.css-1rs6os.edgvbvh3 { display: none !important; }
.stDeployButton { display: none !important; }
.css-16idsys { display: none !important; }
header { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Load credentials from local file if available
if os.path.exists("service_account_credentials.json"):
    with open("service_account_credentials.json", "r") as f:
        GOOGLE_CREDENTIALS = json.load(f)
else:
    if "secrets" in st.__dict__ and "google_sheets" in st.secrets:
        GOOGLE_CREDENTIALS = json.loads(st.secrets["google_sheets"]["credentials"])
    else:
        st.error("No credentials found. Please upload service_account_credentials.json.")
        st.stop()

# Check for placeholder values.
if GOOGLE_CREDENTIALS.get("project_id") == "your-project-id":
    st.error("Detected placeholder credentials. Please update your service_account_credentials.json with real values.")
    st.stop()

# Ensure the private key is formatted correctly.
if "private_key" in GOOGLE_CREDENTIALS:
    key = GOOGLE_CREDENTIALS["private_key"]
    if "\\n" in key:
        key = key.replace("\\n", "\n")
    GOOGLE_CREDENTIALS["private_key"] = key.strip()
    if not GOOGLE_CREDENTIALS["private_key"].startswith("-----BEGIN PRIVATE KEY-----"):
        st.error("Invalid private key format. It should start with '-----BEGIN PRIVATE KEY-----'")
        st.stop()

# Function to fetch API key from Google Sheet using open_by_url
def get_api_key_from_sheet(creds):
    try:
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/12YB3_xHh0ngsh1gwQADC1vpqQFgjuX4x-VvLoD8_7R0/edit")
        worksheet = sheet.get_worksheet(0)
        return worksheet.acell('A1').value
    except Exception as e:
        st.error(f"Error fetching API key from Google Sheet: {e}")
        return None

def extract_text(obj):
    """
    Extracts text from an object as provided by the PDF.
    If the object has a 'value' attribute, return it.
    Otherwise, join any available attribute values (excluding technical ones)
    without adding extra labels.
    """
    if obj is None:
        return "N/A"
    if hasattr(obj, "value"):
        return obj.value
    # Fallback: join all attribute values (exclude known technical keys)
    excluded = {'confidence', 'bounding_box', 'polygon', 'description'}
    values = [str(val) for key, val in obj.__dict__.items() 
              if key.lower() not in excluded and val]
    return "<br>".join(values) if values else "N/A"

def main():
    st.markdown(
        "<h1 style='text-align: center; font-family: \"Times New Roman\", serif; color: red;'>شركة خط الحرير</h1>",
        unsafe_allow_html=True
    )

    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=scopes)
    except Exception as e:
        st.error(f"Error creating credentials: {e}")
        return

    try:
        creds.refresh(Request())
    except Exception as e:
        st.error(f"Failed to validate credentials: {e}")
        return

    api_key = get_api_key_from_sheet(creds)
    if not api_key:
        st.error("Could not retrieve API key from Google Sheet.")
        return

    uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])
    if uploaded_file:
        try:
            with st.spinner("Processing document..."):
                mindee_client = Client(api_key=api_key)
                file_bytes = uploaded_file.read()
                if not file_bytes:
                    st.error("Uploaded file is empty or could not be read.")
                    return

                input_doc = mindee_client.source_from_bytes(file_bytes, uploaded_file.name)
                result: AsyncPredictResponse = mindee_client.enqueue_and_parse(product.BillOfLadingV1, input_doc)

                if result.job.status == "completed" and result.document is not None:
                    prediction = result.document.inference.prediction
                    bol_number = getattr(prediction, 'bill_of_lading_number', None)
                    bol_number = bol_number.value if bol_number else "N/A"
                    
                    # Order fields: BILL OF LADING No., SHIPPER, CONSIGNEE, PORT OF LOADING, PORT OF DISCHARGE.
                    data = {
                        "BILL OF LADING No.": bol_number,
                        "SHIPPER": extract_text(getattr(prediction, 'shipper', None)),
                        "CONSIGNEE": extract_text(getattr(prediction, 'consignee', None)),
                        "PORT OF LOADING": getattr(prediction, 'port_of_loading', None).value if getattr(prediction, 'port_of_loading', None) else "N/A",
                        "PORT OF DISCHARGE": getattr(prediction, 'port_of_discharge', None).value if getattr(prediction, 'port_of_discharge', None) else "N/A"
                    }

                    html_table = """
                    <style>
                        table {width: 100%; border-collapse: collapse; margin: 20px 0; background-color: #ffffff; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden;}
                        th, td {padding: 15px; text-align: left; border-bottom: 1px solid #ddd; vertical-align: top; word-wrap: break-word; max-width: 600px;}
                        th {color: #ff0000; font-weight: bold; font-size: 16px; background-color: #f5f5f5;}
                        td {color: #0000ff; font-size: 14px;}
                    </style>
                    <table>
                    <tr>
                    """
                    for field in data.keys():
                        html_table += f"<th>{field}</th>"
                    html_table += "</tr><tr>"
                    for value in data.values():
                        html_table += f"<td>{value}</td>"
                    html_table += "</tr></table>"

                    st.subheader("Parsed Bill of Lading Information")
                    st.markdown(html_table, unsafe_allow_html=True)
                else:
                    error_msg = result.job.error if result.job.error else "Unknown error"
                    st.error(f"Failed to parse document: {error_msg}")
                    st.json({"job_status": result.job.status, "error": error_msg})
        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            st.write("Exception details:", str(e))

if __name__ == "__main__":
    main()
