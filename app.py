"""
File: app.py
Purpose:
    This Streamlit application serves as the main interface for uploading a PDF Bill of Lading
    and processing it via Mindee’s asynchronous BillOfLadingV1 API. It extracts relevant fields.

Modifications:
    - Removed the GitHub icon and Fork button from the top-right UI.
    - Removed the three-dot menu.
    - Removed the Streamlit branding button at the bottom-right.
    - Ensured the UI is clean and distraction-free.
"""

import streamlit as st
from mindee import Client, product, AsyncPredictResponse

# Hide Streamlit's default UI elements
hide_streamlit_style = """
<style>
/* Hide GitHub icon, Fork button, and three-dot menu */
.viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_, 
.viewerBadge_link__1S137, .viewerBadge_text__1JaDK {
    display: none !important;
}

/* Hide Streamlit branding */
.stDeployButton {display: none !important;}

/* Hide top-right settings menu */
header {visibility: hidden;}

/* Hide the footer */
footer {visibility: hidden;}
</style>
"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def main():
    # Arabic title at the top center with red color
    st.markdown(
        "<h1 style='text-align: center; font-family: \"Times New Roman\", serif; color: red;'>شركة خط الحرير</h1>",
        unsafe_allow_html=True
    )

    # File uploader for PDF only
    uploaded_file = st.file_uploader("Pdf File", type=["pdf"])

    if uploaded_file:
        # Retrieve Mindee API key from secrets
        api_key = st.secrets.get("mindee_api_key", None)
        if not api_key:
            st.error("Mindee API key not found. Please set it in `.streamlit/secrets.toml` as `mindee_api_key`.")
            return

        try:
            with st.spinner("Processing document..."):
                # Initialize Mindee client
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

                    # Helper function to enumerate subfields (like address, email, name, phone)
                    def add_complex_field(header, obj, exclude=None):
                        if exclude is None:
                            exclude = set()
                        if obj:
                            # We'll treat each subfield as a row
                            html = f"<tr><td colspan='2' class='field-header'>{header}</td></tr>"
                            for key, val in obj.__dict__.items():
                                # Skip fields we don't want to display
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
