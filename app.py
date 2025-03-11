import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from mindee import Client, product, AsyncPredictResponse
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Hide Streamlit UI elements
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

# Service account credentials (using the validated private_key)
GOOGLE_CREDENTIALS = {
    "type": "service_account",
    "project_id": "gen-lang-client-0562602106",
    "private_key_id": "52653ed29570ee20de48781476e2f646b346faa9",
    "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQC6VCfEIfk07VZj
45UyVG73uOWHYiEZRFiM8Y9z2EuUn62Wzw3aoyS7YuMXz8d/H0qqmn5bMi6/TO/r
0j5u16ArsClxva9d3x8qLSsKXQI4Fy1g3a+wiws8O2qx4G32cz1zaK611MGFhoii
f80ZdcunyRmN0s39PzfAs+5/Wqw8Zl/iGYIHFNFuWZtR87qY4IC9lu8L2TM6hgH6
pgwehmiBeHyhYoTZ2sZW5J3bWE8IwrEB8X69q8WII+/oKoeQ5DrzjJQqKOaJLEbI
R3Pk5c+R9pJMFz5bkcaukbJXTxAZZP7EbgjkvRnbp827vLhowWhpq/3/wQcyfw51
mOxgcwhjAgMBAAECggEAOJczprGMz0LgMKFf4HPdahZ5e9dVZyenX1NEdvIz7lVa
8wk603MmRlVf1I0SMa1Oz6bxhoAky4wx+CUYOjD6IBq2U6nBN9j6zaP/RPv/nwqH
CTr7T7rDNE11d8XKkAXrHYCnQ2l1RzkXiYcYQ0nQC0scHENwtaA8LiZX4s0mr4cA
6w71scIAKpMYZp8ixOA4qtJ+CH2ETog/bn8FmNhjnNv1+VUjQx9T7RgQSusTJWV1
7bqi+PfXGGZaNI3WsTKTLqL1QxZgzOV6dpzeGVHFLg78xgt2tz7UtaOPwwCyG8mJ
xWDDYv1Nagji38Yu6qKOQHDqHRHN1ry7pJNw/Nj2lQKBgQDyLNJ2UHHtQjRqJPLG
X8igVCgXJEl6av/UfX+n5Vo6xikgFXtvq25tJAWDYN3ozKS6vy164yeQ2ZGa1G46
vN5Q3JeeDVynkCEJOTDXxKc+8cj5G/DFRdB9RUTKuhjHIghfRrCgSBbrvppa0xTf
qTIXdsXRpaQn7ZjuSvZMM8OtjQKBgQDE9y/5vkRcYxlGvDPFViqnWgQ7BXAV4Azj
ey0kfYSvW9HKjysD+Cwx8LTCOUDPwbUIzE+srxrqPk+6aC01EPhLtIA+z6CnVvRR
GcZt2SKkkCaQuzYVWTTDd25+XKX3NoDGk/1bzhyYrcc1GeoEJSBzyLSCGWh3XiAr
tk19Hfc5rwKBgQDEqSlv8vvRVAYEfGS6O2ZM7Ipx4IHa67E8+X0E9vdC61DSQR+w
G2LdNndTrQIH3seW71EbjgO/WS8osIGjKWTP/ZMSQn+PgzeQqeTEE2pNb0NpKAtp
57vbPrkSd/VPII/z7w/X2TLj1jC6uNcmmduXulgCW6Tm18dtG2rPjunEsQKBgQCi
uZVpP0g7C6RWTCZ5YjbbDANyv4tah0AesCUbgJeeSL2KG73uCZp5p+Oukp55BhAK
tMEeaYxS+ifkWS0AKoT4BqftPJv9pFk0p5bIKhv02SMDb6e++3QcCQ/AVcrH8r9x
T9KBhkcZ3Hg35rDvu7yT6701vsgP1jO96V8bfyZBAQKBgQCPQNOqDfaG3anaBg3R
TA69yjI69V38w5U7KeFNYu1WW3LrILx4ePclOyuFCvgM+vmKG9vfzaOkSesw7Ghz
3MnG5QY49FzWNjkiIyIvJHUQya4PT1bXaQhyvgWUb3N7fTEVEE9xYAgXSzqiwzX1
QSWsb6/kY3mlsEnAx4pJr8Wumg==
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
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/12YB3_xHh0ngsh1gwQADC1vpqQFgjuX4x-VvLoD8_7R0/edit")
        worksheet = sheet.get_worksheet(0)
        api_key = worksheet.acell('A1').value
        return api_key
    except Exception as e:
        st.error(f"Error fetching API key from Google Sheet: {e}")
        return None

def main():
    st.markdown(
        "<h1 style='text-align: center; font-family: \"Times New Roman\", serif; color: red;'>شركة خط الحرير</h1>",
        unsafe_allow_html=True
    )

    # Validate the private key
    try:
        private_key = serialization.load_pem_private_key(
            GOOGLE_CREDENTIALS["private_key"].encode(),
            password=None,
            backend=default_backend()
        )
        st.write("Private key loaded successfully.")
    except Exception as e:
        st.error(f"Failed to load private key: {e}")
        return

    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=scopes)

    # Validate credentials
    try:
        creds.refresh(Request())
        st.write("Service account credentials are valid.")
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
                    bol_number = getattr(prediction, 'bill_of_lading_number', None).value if getattr(prediction, 'bill_of_lading_number', None) else "N/A"
                    shipper = getattr(prediction, 'shipper', None)
                    consignee = getattr(prediction, 'consignee', None)
                    port_of_loading = getattr(prediction, 'port_of_loading', None).value if getattr(prediction, 'port_of_loading', None) else "N/A"
                    port_of_discharge = getattr(prediction, 'port_of_discharge', None).value if getattr(prediction, 'port_of_discharge', None) else "N/A"
                    date_of_issue = getattr(prediction, 'date_of_issue', None).value if getattr(prediction, 'date_of_issue', None) else "None"
                    departure_date = getattr(prediction, 'departure_date', None).value if getattr(prediction, 'departure_date', None) else "None"

                    html_table = """
                    <style>
                        table {width: 100%; border-collapse: collapse; margin: 20px 0; background-color: #ffffff; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden;}
                        td {padding: 15px; text-align: left; border-bottom: 1px solid #ddd; vertical-align: top;}
                        .field-header {color: #ff0000; font-weight: bold; font-size: 16px; background-color: #f5f5f5;}
                        .value {color: #0000ff; font-size: 14px; word-wrap: break-word; max-width: 600px;}
                        .subfield {font-size: 14px; color: #333; padding-left: 25px;}
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

                    exclude_fields = {'confidence', 'bounding_box', 'polygon', 'description'}
                    html_table += add_simple_field("BILL OF LADING No.", bol_number)
                    html_table += add_complex_field("SHIPPER", shipper, exclude=exclude_fields)
                    html_table += add_complex_field("CONSIGNEE", consignee, exclude=exclude_fields)
                    html_table += add_simple_field("PORT OF LOADING", port_of_loading)
                    html_table += add_simple_field("PORT OF DISCHARGE", port_of_discharge)
                    html_table += add_simple_field("DATE OF ISSUE", date_of_issue)
                    html_table += add_simple_field("DEPARTURE DATE", departure_date)
                    html_table += "</table>"

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