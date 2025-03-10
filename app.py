"""
Purpose:
    This Streamlit app is the main interface for the AI-BOL-POC application.
    It allows users to upload a Bill of Lading document (PDF, JPG, or PNG) and processes
    it using Mindee's asynchronous API via the Python SDK. The app displays only the requested
    fields in a polished HTML table with field names in red and values in blue.

Requested Fields:
    - BILL OF LADING No.
    - SHIPPER (with relevant subfields)
    - CONSIGNEE (with relevant subfields)
    - VESSEL AND VOYAGE NO.
    - PORT OF LOADING
    - PORT OF DISCHARGE
    - PORT OF DISCHARGE AGENT

Excluded Fields:
    - Confidence
    - Bounding_box
    - Polygon
    - Description of Packages and Goods
    - Container details
    - Gross Cargo Weight

Installation and Setup:
    - Ensure Python 3.x is installed.
    - Install required packages:
          pip install streamlit requests pandas mindee
    - Set your Mindee API key in `.streamlit/secrets.toml`:
          mindee_api_key = "your_actual_api_key"
    - No hardcoded file paths; users upload via the webpage.

Usage Instructions:
    1. Save this file as `app.py` in your project folder (e.g., F:\projects\AI-BOL-POC).
    2. Open a terminal in that directory.
    3. Run the app:
          streamlit run app.py
    4. Upload a Bill of Lading document to view the parsed results in the browser.

Educational Notes:
    - `enqueue_and_parse` submits the document and polls until the prediction is ready.
    - Only the specified fields are extracted and displayed, with exclusions applied.
    - Uploaded files are processed as bytes with the filename to determine file type.
"""

import streamlit as st
from mindee import Client, product, AsyncPredictResponse

def main():
    st.title("Bill of Lading Parser - AI-BOL-POC")

    # File uploader widget for supported file types
    uploaded_file = st.file_uploader("Upload a Bill of Lading", type=["pdf", "jpg", "png"])

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

                # Read uploaded file as bytes
                file_bytes = uploaded_file.read()
                if not file_bytes:
                    st.error("Uploaded file is empty or could not be read.")
                    return

                input_doc = mindee_client.source_from_bytes(file_bytes, uploaded_file.name)

                # Submit for asynchronous parsing with BillOfLadingV1
                result: AsyncPredictResponse = mindee_client.enqueue_and_parse(
                    product.BillOfLadingV1,
                    input_doc,
                )

                # Process result if parsing succeeded
                if result.job.status == "completed" and result.document is not None:
                    # Access prediction object
                    prediction = result.document.inference.prediction

                    # Debug: Display all attributes and raw dictionary
                    st.write("Available prediction attributes (dir):", dir(prediction))
                    st.write("Raw prediction dictionary (__dict__):", prediction.__dict__)

                    # Extract only the requested fields with fallback to "N/A"
                    bol_number = getattr(prediction, 'bill_of_lading_number', None)
                    bol_number = bol_number.value if bol_number else "N/A"

                    shipper = getattr(prediction, 'shipper', None)
                    consignee = getattr(prediction, 'consignee', None)

                    # Extract VESSEL AND VOYAGE NO.
                    # Check raw dict for possible vessel/voyage fields if not in dir()
                    vessel_voyage = "N/A"  # Default
                    if 'vessel' in prediction.__dict__ and 'voyage' in prediction.__dict__:
                        vessel = prediction.__dict__['vessel']
                        voyage = prediction.__dict__['voyage']
                        vessel_voyage = f"{vessel.value} {voyage.value}" if vessel and voyage else "N/A"
                    elif 'vessel_and_voyage_no' in prediction.__dict__:
                        vessel_voyage_obj = prediction.__dict__['vessel_and_voyage_no']
                        vessel_voyage = vessel_voyage_obj.value if vessel_voyage_obj else "N/A"

                    port_of_loading = getattr(prediction, 'port_of_loading', None)
                    port_of_loading = port_of_loading.value if port_of_loading else "N/A"

                    port_of_discharge = getattr(prediction, 'port_of_discharge', None)
                    port_of_discharge = port_of_discharge.value if port_of_discharge else "N/A"

                    discharge_agent = getattr(prediction, 'port_of_discharge_agent', None)
                    discharge_agent = discharge_agent.value if discharge_agent else "N/A"

                    # Define polished HTML table with CSS styling
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

                    # Helper function to add simple fields
                    def add_simple_field(field_name, value):
                        return f"<tr><td class='field-header'>{field_name}</td><td class='value'>{value}</td></tr>"

                    # Helper function to add complex fields with exclusions
                    def add_complex_field(header, obj, exclude=None):
                        if exclude is None:
                            exclude = set()
                        if obj:
                            html = f"<tr><td colspan='2' class='field-header'>{header}</td></tr>"
                            for key, value in obj.__dict__.items():
                                if key.lower() not in exclude:
                                    html += f"<tr><td class='subfield'>{key.capitalize()}</td><td class='value'>{value}</td></tr>"
                            return html
                        return f"<tr><td class='field-header'>{header}</td><td class='value'>N/A</td></tr>"

                    # Fields to exclude
                    exclude_fields = {'confidence', 'bounding_box', 'polygon', 'description'}

                    # Add only the requested fields to the table
                    html_table += add_simple_field("BILL OF LADING No.", bol_number)
                    html_table += add_complex_field("SHIPPER", shipper, exclude=exclude_fields)
                    html_table += add_complex_field("CONSIGNEE", consignee, exclude=exclude_fields)
                    html_table += add_simple_field("VESSEL AND VOYAGE NO.", vessel_voyage)
                    html_table += add_simple_field("PORT OF LOADING", port_of_loading)
                    html_table += add_simple_field("PORT OF DISCHARGE", port_of_discharge)
                    html_table += add_simple_field("PORT OF DISCHARGE AGENT", discharge_agent)
                    html_table += "</table>"

                    # Render the polished table
                    st.subheader("Parsed Bill of Lading Information")
                    st.markdown(html_table, unsafe_allow_html=True)

                else:
                    # Handle API errors
                    error_msg = result.job.error if result.job.error else "Unknown error"
                    st.error(f"Failed to parse document: {error_msg}")
                    st.json({"job_status": result.job.status, "error": error_msg})

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            st.write("Exception details:", str(e))

if __name__ == "__main__":
    main()