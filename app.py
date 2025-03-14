# =======================================================================
# File: app.py
#
# Purpose:
#   Main Streamlit application file for the AI-BOL-POC-GPT4oMini project.
#
# Role:
#   - Handles file upload for a text-based PDF (with OCR fallback for image-based pages).
#   - Extracts text from the PDF using pdfplumber; if no text is found on a page, uses pytesseract OCR.
#   - Sends the extracted text to GPT-4o-mini for structured Bill of Lading data extraction.
#   - Displays parsed Bill of Lading data along with additional "Details" fields (Notify Parties, etc.).
#   - Shows API token usage and cost (in cents) based on GPT-4o-mini pricing.
#
# Workflow:
#   1. User uploads a PDF.
#   2. pdfplumber extracts text from each page; OCR fallback if text is empty.
#   3. The extracted text is sent to GPT-4o-mini with a prompt requesting:
#      - Basic Fields (B/L No., Shipper, Consignee, Ports, etc.)
#      - Additional Details (Notify Parties, Vessel & Voyage, Container Info, etc.)
#   4. The JSON response is parsed into two tables:
#        - "Parsed Bill of Lading Information" for the main fields.
#        - "Details" for extended info, plus a separate container info table if present.
#   5. Token usage and cost are calculated and displayed.
#
# Integration:
#   Uses OpenAI’s ChatCompletion API with model "gpt-4o-mini" to process extracted text.
#
# Note:
#   This version is designed for Streamlit Cloud, requiring:
#     - pdfplumber + pytesseract (with Tesseract installed in the environment).
#     - White-space styling for multiline content.
#     - Minimizing LLM variability (temperature=0) and increased max_tokens=2048.
# =======================================================================

import streamlit as st
import requests
import pandas as pd
import openai
import json
import pdfplumber
import pytesseract
from PIL import Image
from io import BytesIO

# Hide unnecessary Streamlit UI elements
hide_streamlit_style = """
<style>
.viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_, 
.viewerBadge_link__1S137, .viewerBadge_text__1JaDK, header, footer {
    display: none !important;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def get_api_key():
    """
    Retrieves the GPT-4o Mini API key from Streamlit secrets.
    The API key must be stored in .streamlit/secrets.toml under 'api-key-gpt-4o-mini'.
    """
    try:
        api_key = st.secrets["api-key-gpt-4o-mini"]
        if not api_key:
            st.error("API key is missing in the secrets file.")
        return api_key
    except Exception as e:
        st.error(f"Error retrieving API key from secrets: {e}")
        return None

def extract_text_from_pdf(file_bytes):
    """
    Uses pdfplumber to extract text from each page of the PDF.
    If a page has no extractable text, falls back to OCR with pytesseract.
    Returns concatenated text from all pages.
    """
    text = ""
    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            if not pdf.pages:
                st.error("No pages found in the PDF.")
                return None
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    st.info("No text detected on a page; using OCR fallback.")
                    pil_image = page.to_image(resolution=300).original
                    ocr_text = pytesseract.image_to_string(pil_image)
                    if ocr_text:
                        text += ocr_text + "\n"
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None
    return text.strip()

def call_gpt4o_mini_text_api(pdf_text, api_key):
    """
    Sends the extracted PDF text to GPT-4o-mini for structured data extraction.
    Prompt requests:
      - Basic Fields (B/L No., Shipper, Consignee, Port of Loading, Port of Discharge)
      - Additional Details (Notify Parties, Port of Discharge Agent, Vessel & Voyage No, Booking Ref,
        Number of Containers, and container_info array).
    Emphasizes not to summarize or omit details, and sets temperature=0, max_tokens=2048.
    """
    prompt = (
        "You are given text from a Bill of Lading document. "
        "Return all fields exactly as found in the text, without summarizing or truncating. "
        "Use null for missing fields.\n\n"
        "Extract the following fields:\n"
        "  1. Basic Fields:\n"
        "     - Bill of Lading No.\n"
        "     - Shipper\n"
        "     - Consignee\n"
        "     - Port of Loading\n"
        "     - Port of Discharge\n\n"
        "  2. Additional Details:\n"
        "     - NOTIFY PARTIES\n"
        "     - PORT OF DISCHARGE AGENT\n"
        "     - VESSEL AND VOYAGE NO\n"
        "     - BOOKING REF.\n"
        "     - Number of Containers\n"
        "     - container_info (array of objects): container_number, seal_number, container_size, "
        "       tare_weight, description_of_packages_and_goods, gross_cargo_weight\n\n"
        "Return the result in JSON format with keys:\n"
        "  - bill_of_lading_number, shipper, consignee, port_of_loading, port_of_discharge,\n"
        "    notify_parties, port_of_discharge_agent, vessel_and_voyage_no, booking_ref,\n"
        "    number_of_containers, container_info.\n\n"
        "Text:\n'''{}'''".format(pdf_text)
    )
    openai.api_key = api_key
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Hypothetical GPT-4o-mini model
            messages=[
                {"role": "system", "content": "You are an assistant that processes Bill of Lading text and returns structured JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0,      # Minimizes variability
            max_tokens=2048     # Allows enough space for a full response
        )
        return response
    except openai.error.OpenAIError as oe:
        st.error(f"OpenAI API error: {oe}")
        return None

def format_field(value):
    """Replace newlines with <br> for HTML display."""
    if value is None:
        return "N/A"
    return str(value).replace("\n", "<br>")

def main():
    st.markdown("<h1 style='text-align: center; color: red;'>شركة خط الحرير</h1>", unsafe_allow_html=True)

    api_key = get_api_key()
    if not api_key:
        return

    uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])
    if uploaded_file:
        with st.spinner("Processing PDF..."):
            file_bytes = uploaded_file.read()
            if not file_bytes:
                st.error("Uploaded file is empty or could not be read.")
                return

            pdf_text = extract_text_from_pdf(file_bytes)
            if not pdf_text:
                st.warning("No text found in this PDF even after OCR fallback. Please try another PDF.")
                return

            response = call_gpt4o_mini_text_api(pdf_text, api_key)
            if response is None:
                return

            # Parse JSON from the API response
            message_content = response["choices"][0]["message"]["content"]
            try:
                prediction = json.loads(message_content)
            except json.JSONDecodeError as je:
                st.error(f"Failed to decode JSON from API response: {je}")
                st.text("Raw response:")
                st.text(message_content)
                return

            # Basic Fields
            extracted_data = {
                "BILL OF LADING No.": format_field(prediction.get("bill_of_lading_number")),
                "SHIPPER": format_field(prediction.get("shipper")),
                "CONSIGNEE": format_field(prediction.get("consignee")),
                "PORT OF LOADING": format_field(prediction.get("port_of_loading")),
                "PORT OF DISCHARGE": format_field(prediction.get("port_of_discharge"))
            }

            st.subheader("Parsed Bill of Lading Information")
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

            # Additional Details
            details_data = {
                "NOTIFY PARTIES": format_field(prediction.get("notify_parties")),
                "PORT OF DISCHARGE AGENT": format_field(prediction.get("port_of_discharge_agent")),
                "VESSEL AND VOYAGE NO": format_field(prediction.get("vessel_and_voyage_no")),
                "BOOKING REF.": format_field(prediction.get("booking_ref")),
                "Number of Containers": format_field(prediction.get("number_of_containers"))
            }

            st.subheader("Details")
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

            # Container Information
            container_info = prediction.get("container_info")
            if container_info and isinstance(container_info, list) and len(container_info) > 0:
                st.subheader("Container Information")
                df_containers = pd.DataFrame(container_info)
                # Rename columns for display if needed
                df_containers = df_containers.rename(columns={
                    "container_number": "Container Number",
                    "seal_number": "Seal Number",
                    "container_size": "Container Size",
                    "tare_weight": "Tare Weight",
                    "description_of_packages_and_goods": "Description of Packages and Goods",
                    "gross_cargo_weight": "Gross Cargo Weight"
                })
                st.table(df_containers)

            # Token Usage & Cost
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            # GPT-4o mini pricing:
            #   Input tokens: $0.150 per 1M => cost_prompt_cents
            #   Output tokens: $0.600 per 1M => cost_completion_cents
            cost_prompt_cents = prompt_tokens * (0.150 / 1e6 * 100)
            cost_completion_cents = completion_tokens * (0.600 / 1e6 * 100)
            cost_total_cents = cost_prompt_cents + cost_completion_cents

            df_token_cost = pd.DataFrame({
                "In Tokens (Prompt)": [prompt_tokens],
                "Out Tokens (Completion)": [completion_tokens],
                "Total Tokens": [total_tokens],
                "Cost (cents)": [f"{cost_total_cents:.2f}"]
            })
            df_token_cost.index = ["" for _ in range(len(df_token_cost))]
            styled_table = df_token_cost.style.set_properties(**{'text-align': 'left'}).to_html()

            st.subheader("API Token Usage and Cost")
            st.markdown(styled_table, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
