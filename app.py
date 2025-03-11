import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials
from mindee import Client, product, AsyncPredictResponse

# Hide Streamlit's UI elements (branding, profile, menu, GitHub)
hide_streamlit_style = """
<style>
/* Hide GitHub icon, Fork button, and three-dot menu */
.viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_, 
.viewerBadge_link__1S137, .viewerBadge_text__1JaDK {
    display: none !important;
}

/* Hide the three-dot menu */
.css-1rs6os.edgvbvh3 {
    display: none !important;
}

/* Hide Streamlit branding */
.stDeployButton {display: none !important;}

/* Hide user profile icon */
.css-16idsys {
    display: none !important;
}

/* Hide top-right settings menu */
header {visibility: hidden;}

/* Hide the footer */
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Service account credentials from your provided JSON
GOOGLE_CREDENTIALS = {
    "type": "service_account",
    "project_id": "gen-lang-client-0562602106",
    "private_key_id": "0a0dfaaa7fe83cd7abbb40a9a201eef6f64a35d3",
    "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDI8j6uYtjXmTV8
eW7Z7lrTc5mwqp078o0GtPo/J81mZCzIhjLMg5OoPCtA0Jzw4BeTK5kl/s0bLLtP
MGbnQ4md9rX4rFxNm3uf21cJ9UBk97SvsYRm8niQDQJHcfojiCDvV568xwrgvOTo
dGVB0O53we+EGU9z9qRa0xW6k9WT80jbWOJHn/tBj4fv0PmfUk9mHciv/KHS5Xxb
yS1wR0PUaKJHmcpOwArrVjF5+BSuUz/aK3YpG+1Lq1QXoxgpFFyFsk4zsimKJhBa
ZC0kcfqLCVQVbNjwSJJ3X99bOkU6xQA4gWnCcyhRsAiIqIDIQRN1zjD/4DIJU9gr
OVmF1lynAgMBAAECggEATm46p9796tyqQyy0ZwxA2BJhNNLK7wiDIdCGchsLcQD9
d8DlV+ytN7dQXIpwDxYwLWmRa4KRtJ8XdteZ+n7iWkzehrJjjoj2zhSS2timKyKB
nCep2XKfOv5Q2ujyLGcoD7L/yofXx5MCt3YixXcSdJy16zXjzIvCZ47HBt1HuehD
RP2nHO0BFlUNkvd8+7nRkyaqxOtBL0ePtINUiHWwT+nE/PRzx9T0Ys3hqsJIKbnS
2puBE7TK1BVqO/niMewkTRMJBONjDRozNnYSnTtxNPiPFBnozTpB27+tm2uhjAbx
EfpwTUe/zxvr38xGn9rLAtL2m5UTMyTntQq5nvvPoQKBgQD/ZHp+RGyryNzzze7a
/6jyAg06HY8i9CAkFQWU2eW34qI+tqjA2QX6yb1phN1OXVbsYTQ7H9nLpirFu8sh
k4JHKkKTipVqvUAbci1Igk/OzwNdBZt9n1Dwh8Sanzi2DH76IdDnV5NdBWZ3QPUp
xcVrlDcHPSJxRuHdiPE/sb2axwKBgQDJbJx8ou1asnUZsGlrILeHNGTin5kYLsCh
luICi1wo3TPh8fRv9EAywFnryOPC6yY0LFNnDy8zb93lzMSSK7j2Wu174Y71FsZg
069k0qv6D4CjSHkpfClL5aIXJFPGhLud8i9nO8ft22oopON/zRIymytaO+vjGEht
YFbqh05PIQKBgHcaAbIO8Orv4nLkj8abwcsSv95hWJZBaRfKoe6361RlIarDflFp
JEu/d1DVQGvCRb442qXUBbreREYwfNusse3EPIYX8/RyS4pBJfMRqmxUyEnCSrA7
8wApILvHEyh7DWBTEtxAUB3qXc2xgmO3soin9z2t+fj/yGeK7I76seSTAoGBAJ6s
M74vbwFSsdKx2OmuVUVqLcsk5KpbMh5ZSOOuOsRqNRPZ0bBb3jLcujl3AI0tRuQ0
wuLd4FYJ2ujLXVK0pLlVOd2r+zzxWwct2u5200li6vg2AFSA3dtPI1hNor0xFMdA
4LzXKBElFsS72Ad2Wc6J1CX6LEGygGPBT9bjDfphAoGAadeyUF5F9tMf5e1QK5DU
jm3mRiHzkU/ugxP/z7uCOk56s885PyG/Ti2ulqdWp/OXKpyuop380aB7Mhztd7cM
t0pGPiBNzEoIXh8FxM3QyMDHFIHMyFHViaOpTs2MhiUfR4mJC3Qi7yZZQGk8dDey
Prr6vC9C61D2XAhAitG0/nU=
-----END PRIVATE KEY-----
""",
    "client_email": "my-sheets-service-account@gen-lang-client-0562602106.iam.gserviceaccount.com",
    "client_id": "111456377330651431387",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/my-sheets-service-account%40gen-lang-client-0562602106.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

# Function to fetch API key from Google Sheet
def get_api_key_from_sheet(creds):
    try:
        # Authenticate with Google Sheets
        client = gspread.authorize(creds)
        
        # Open the Google Sheet (replace with your actual sheet URL or ID)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/12YB3_xHh0ngsh1gwQADC1vpqQFgjuX4x-VvLoD8_7R0/edit?pli=1&gid=0#gid=0")  # Replace with your sheet URL
        worksheet = sheet.get_worksheet(0)  # Use the first worksheet
        
        # Assuming the API key is in cell A1 (adjust as needed)
        api_key = worksheet.acell('A1').value
        return api_key
    except Exception as e:
        st.error(f"Error fetching API key from Google Sheet: {e}")
        return None

def main():
    # Arabic title at the top center with red color
    st.markdown(
        "<h1 style='text-align: center; font-family: \"Times New Roman\", serif; color: red;'>شركة خط الحرير</h1>",
        unsafe_allow_html=True
    )

    # Define scopes required for Google Sheets access
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # Create credentials object
    creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=scopes)

    # Fetch API key from Google Sheet
    api_key = get_api_key_from_sheet(creds=creds)
    if not api_key:
        st.error("Could not retrieve API key from Google Sheet.")
        return

    # File uploader for PDF only
    uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])

    if uploaded_file:
        try:
            with st.spinner("Processing document..."):
                # Initialize Mindee client with the fetched API key
                mindee_client = Client(api_key=api_key)

                # Read uploaded file bytes
                file_bytes = uploaded_file.read()
                if not file_bytes:
                    st.error("Uploaded file is empty or could not be read.")
                    return

                # Create input_doc from bytes
                input_doc = mindee_client.source_from_bytes(file_bytes, uploaded_file.name)

                # Submit for asynchronous parsing
                result: AsyncPredictResponse = mindee_client.enqueue_and_parse(
                    product.BillOfLadingV1,
                    input_doc,
                )

                # Check if parsing succeeded
                if result.job.status == "completed" and result.document is not None:
                    prediction = result.document.inference.prediction

                    # Extract main fields
                    bol_number = getattr(prediction, 'bill_of_lading_number', None)
                    bol_number = bol_number.value if bol_number else "N/A"

                    shipper = getattr(prediction, 'shipper', None)
                    consignee = getattr(prediction, 'consignee', None)

                    port_of_loading = getattr(prediction, 'port_of_loading', None)
                    port_of_loading = port_of_loading.value if port_of_loading else "N/A"

                    port_of_discharge = getattr(prediction, 'port_of_discharge', None)
                    port_of_discharge = port_of_discharge.value if port_of_discharge else "N/A"

                    date_of_issue = getattr(prediction, 'date_of_issue', None)
                    date_of_issue = date_of_issue.value if date_of_issue else "None"

                    departure_date = getattr(prediction, 'departure_date', None)
                    departure_date = departure_date.value if departure_date else "None"

                    # HTML table styling
                    html_table = """
                    <style>
                        table {
                            width: 100%;
                            border-collapse: collapse;
                            margin: 20px 0;
                            background-color: #ffffff;
                            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                            border-radius: 8px;
                            overflow: hidden;
                        }
                        td {
                            padding: 15px;
                            text-align: left;
                            border-bottom: 1px solid #ddd;
                            vertical-align: top;
                        }
                        .field-header {
                            color: #ff0000;
                            font-weight: bold;
                            font-size: 16px;
                            background-color: #f5f5f5;
                        }
                        .value {
                            color: #0000ff;
                            font-size: 14px;
                            word-wrap: break-word;
                            max-width: 600px;
                        }
                        .subfield {
                            font-size: 14px;
                            color: #333;
                            padding-left: 25px;
                        }
                    </style>
                    <table>
                    """

                    def add_simple_field(field_name, value):
                        return f"<tr><td class='field-header'>{field_name}</td><td class='value'>{value}</td></tr>"

                    def add_complex_field(header, obj, exclude=None):
                        if exclude is None:
                            exclude = set()
                        if obj:
                            html = f"<tr><td colspan='2' class='field-header'>{header}</td></tr>"
                            for key, val in obj.__dict__.items():
                                if key.lower() not in exclude:
                                    html += f"<tr><td class='subfield'>{key.capitalize()}</td><td class='value'>{val}</td></tr>"
                            return html
                        return f"<tr><td class='field-header'>{header}</td><td class='value'>N/A</td></tr>"

                    # Fields to exclude
                    exclude_fields = {'confidence', 'bounding_box', 'polygon', 'description'}

                    # Build table rows
                    html_table += add_simple_field("BILL OF LADING No.", bol_number)
                    html_table += add_complex_field("SHIPPER", shipper, exclude=exclude_fields)
                    html_table += add_complex_field("CONSIGNEE", consignee, exclude=exclude_fields)
                    html_table += add_simple_field("PORT OF LOADING", port_of_loading)
                    html_table += add_simple_field("PORT OF DISCHARGE", port_of_discharge)
                    html_table += add_simple_field("DATE OF ISSUE", date_of_issue)
                    html_table += add_simple_field("DEPARTURE DATE", departure_date)
                    html_table += "</table>"

                    # Display the final table
                    st.subheader("Parsed Bill of Lading Information")
                    st.markdown(html_table, unsafe_allow_html=True)

                else:
                    # Handle Mindee job errors
                    error_msg = result.job.error if result.job.error else "Unknown error"
                    st.error(f"Failed to parse document: {error_msg}")
                    st.json({"job_status": result.job.status, "error": error_msg})

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            st.write("Exception details:", str(e))

if __name__ == "__main__":
    main()