# app.py
"""
Purpose:
    This is the main entry point for the AI-BOL-POC application.
    It provides a Streamlit-based UI for uploading PDF files and displaying extracted Bill of Lading information.
Role:
    - Handles user interactions (file upload, OCR method selection).
    - Orchestrates the PDF processing and API extraction by calling functions from pdf_processing and api_services modules.
Workflow:
    - User uploads a PDF file.
    - The app calls extract_text_from_pdf_with_image_fallback from pdf_processing.
    - The extracted text is sent to GPT-4o-mini via call_gpt4o_mini_text_api from api_services.
    - The structured JSON response is parsed and displayed in tables.
"""

import streamlit as st
import json
import pandas as pd
from pdf_processing import extract_text_from_pdf_with_image_fallback
from api_services import call_gpt4o_mini_text_api, get_api_key

# Hide default Streamlit UI elements with custom CSS.
hide_streamlit_style = """
<style>
.viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_,
.viewerBadge_link__1S137, .viewerBadge_text__1JaDK, header, footer {
    display: none !important;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def format_field(value):
    """
    Formats a field value for HTML display in tables by replacing newlines with <br>.
    """
    if value is None:
        return "N/A"
    return str(value).replace("\n", "<br>")

def main():
    st.markdown("<h1 style='text-align: center; color: red;'>شركة خط الحرير</h1>", unsafe_allow_html=True)

    # Let user select the OCR method for image-based processing.
    ocr_choice = st.radio(
        "Select model for image-based processing:",
        ("Google Cloud Vision", "GPT-4", "Mistral OCR"),
        index=0
    )

    api_key = get_api_key()
    if not api_key:
        return

    # File uploader for PDF files.
    uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])
    if uploaded_file:
        file_bytes = uploaded_file.read()
        if not file_bytes:
            st.error("Uploaded file is empty or could not be read.")
            return

        with st.spinner("Processing PDF..."):
            combined_text, image_usage, gcv_count = extract_text_from_pdf_with_image_fallback(file_bytes, ocr_choice)

        if not combined_text:
            st.warning("No text could be extracted from the PDF (even after OCR).")
            return

        # Send the combined text to GPT-4o-mini for structured Bill of Lading extraction.
        response = call_gpt4o_mini_text_api(combined_text, api_key)
        if not response:
            return

        try:
            message_content = response["choices"][0]["message"]["content"]
            prediction = json.loads(message_content)
        except (KeyError, json.JSONDecodeError) as e:
            st.error(f"Failed to decode JSON from GPT-4o-mini response: {e}")
            st.text("Raw response:")
            st.text(json.dumps(response, indent=2))
            return

        # Display "Parsed Bill of Lading Information" table.
        st.subheader("Parsed Bill of Lading Information")
        extracted_data = {
            "BILL OF LADING No.": format_field(prediction.get("bill_of_lading_number")),
            "SHIPPER": format_field(prediction.get("shipper")),
            "CONSIGNEE": format_field(prediction.get("consignee")),
            "PORT OF LOADING": format_field(prediction.get("port_of_loading")),
            "PORT OF DISCHARGE": format_field(prediction.get("port_of_discharge"))
        }
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
            th, td {
                padding: 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
                vertical-align: top;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            th {
                color: #ff0000;
                font-weight: bold;
                font-size: 16px;
                background-color: #f5f5f5;
            }
            td {
                color: #0000ff;
                font-size: 14px;
            }
        </style>
        <table>
        <tr>
        """
        for field in extracted_data.keys():
            html_table += f"<th>{field}</th>"
        html_table += "</tr><tr>"
        for value in extracted_data.values():
            html_table += f"<td>{value}</td>"
        html_table += "</tr></table>"
        st.markdown(html_table, unsafe_allow_html=True)

        # Display "Details" table.
        st.subheader("Details")
        details_data = {
            "NOTIFY PARTIES": format_field(prediction.get("notify_parties")),
            "PORT OF DISCHARGE AGENT": format_field(prediction.get("port_of_discharge_agent")),
            "VESSEL AND VOYAGE NO": format_field(prediction.get("vessel_and_voyage_no")),
            "BOOKING REF.": format_field(prediction.get("booking_ref")),
            "Number of Containers": format_field(prediction.get("number_of_containers"))
        }
        details_table = """
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
            th, td {
                padding: 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
                vertical-align: top;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            th {
                color: #ff0000;
                font-weight: bold;
                font-size: 16px;
                background-color: #f5f5f5;
            }
            td {
                color: #0000ff;
                font-size: 14px;
            }
        </style>
        <table>
        """
        for key, value in details_data.items():
            details_table += f"<tr><th>{key}</th><td>{value}</td></tr>"
        details_table += "</table>"
        st.markdown(details_table, unsafe_allow_html=True)

        # Display "Container Information" if available.
        container_info = prediction.get("container_info")
        if container_info and isinstance(container_info, list) and len(container_info) > 0:
            st.subheader("Container Information")
            df_containers = pd.DataFrame(container_info)
            df_containers = df_containers.rename(columns={
                "container_number": "Container Number",
                "seal_number": "Seal Number",
                "container_size": "Container Size",
                "tare_weight": "Tare Weight",
                "description_of_packages_and_goods": "Description of Packages and Goods",
                "gross_cargo_weight": "Gross Cargo Weight"
            })
            st.table(df_containers)

        # Display API Token Usage and Cost.
        st.subheader("API Token Usage and Cost")
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        cost_prompt_cents = (prompt_tokens / 1_000_000) * 0.15 * 100
        cost_completion_cents = (completion_tokens / 1_000_000) * 0.60 * 100
        text_cost = cost_prompt_cents + cost_completion_cents

        if ocr_choice == "Google Cloud Vision":
            st.markdown("**Image-based Extraction (Google Cloud Vision)**")
            st.markdown(f"Processed {gcv_count} pages with Google Cloud Vision => 0.00 cents (example)")
            image_cost_cents = 0
        elif ocr_choice == "GPT-4":
            st.markdown("**Image-based Extraction (GPT-4)**")
            image_cost_cents = 0
        else:
            st.markdown("**Image-based Extraction (Mistral OCR)**")
            st.markdown("Cost calculation for Mistral OCR is not implemented. Refer to docs.")
            image_cost_cents = 0

        total_cost = text_cost + image_cost_cents
        st.markdown(f"**Total Combined Estimated Cost:** {total_cost:.2f} cents")

if __name__ == "__main__":
    main()
