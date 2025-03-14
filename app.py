# =======================================================================
# File: app.py
#
# Purpose:
#   Main Streamlit application file for the AI-BOL-POC-GPT4oMini project.
#
# Role:
#   - Handles user interactions, including file upload for a text-based PDF.
#   - Extracts text from the PDF using pdfplumber.
#   - Sends the extracted text to GPT-4o-mini for structured Bill of Lading data extraction.
#   - Displays:
#       • Parsed Bill of Lading data,
#       • API token usage (prompt vs. completion), total tokens, and cost.
#
# Workflow:
#   1. User uploads a text-based PDF.
#   2. The PDF is processed by pdfplumber to extract text.
#   3. The extracted text is sent to GPT-4o-mini (via /v1/chat/completions) with a prompt for field extraction.
#   4. The response is parsed and displayed, including token usage and cost.
#
# Integration:
#   This file uses OpenAI’s ChatCompletion API with model "gpt-4o-mini"
#   to process extracted text and return structured JSON outputs.
#
# Note:
#   This version is intended for text-based PDFs only. It is designed to run on Streamlit Cloud.
# =======================================================================

import streamlit as st
import requests
import pandas as pd
import openai
import json
import pdfplumber
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
    The API key must be stored in .streamlit/secrets.toml under the key 'api-key-gpt-4o-mini'.
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
    Uses pdfplumber to extract text from a text-based PDF.
    Wraps the PDF bytes in a BytesIO object so that pdfplumber can seek properly.
    Returns the concatenated text from all pages.
    """
    text = ""
    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None
    return text.strip()

def call_gpt4o_mini_text_api(pdf_text, api_key):
    """
    Sends the extracted PDF text to GPT-4o-mini for structured data extraction.
    Returns the API response.
    """
    prompt = (
        "You are given text from a Bill of Lading document. Extract the following fields: "
        "Bill of Lading No., Shipper, Consignee, Port of Loading, Port of Discharge. "
        "Return the result in JSON format with keys: bill_of_lading_number, shipper, consignee, "
        "port_of_loading, port_of_discharge. Use null for missing fields.\n\n"
        f"Text:\n'''{pdf_text}'''"
    )
    openai.api_key = api_key
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Hypothetical GPT-4o-mini model
            messages=[
                {"role": "system", "content": "You are an assistant that processes text-based PDFs and returns information in JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return response
    except openai.error.OpenAIError as oe:
        st.error(f"OpenAI API error: {oe}")
        return None

def format_field(value):
    """Formats a field for HTML display by replacing newlines with <br> tags."""
    if value is None:
        return "N/A"
    return str(value).replace("\n", "<br>")

def main():
    st.markdown("<h1 style='text-align: center; color: red;'>شركة خط الحرير</h1>", unsafe_allow_html=True)

    api_key = get_api_key()
    if not api_key:
        return

    uploaded_file = st.file_uploader("Upload Text-Based PDF File", type=["pdf"])
    if uploaded_file:
        with st.spinner("Processing text-based PDF..."):
            file_bytes = uploaded_file.read()
            if not file_bytes:
                st.error("Uploaded file is empty or could not be read.")
                return

            pdf_text = extract_text_from_pdf(file_bytes)
            if not pdf_text:
                st.warning("No text found in this PDF. It may be an image-based PDF. Please try a text-based PDF.")
                return

            response = call_gpt4o_mini_text_api(pdf_text, api_key)
            if response is None:
                return

            message_content = response["choices"][0]["message"]["content"]
            try:
                prediction = json.loads(message_content)
            except json.JSONDecodeError as je:
                st.error(f"Failed to decode JSON from API response: {je}")
                st.text("Raw response:")
                st.text(message_content)
                return

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
                table {width: 100%; border-collapse: collapse; margin: 20px 0; background-color: #ffffff; 
                       box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden;}
                th, td {padding: 15px; text-align: left; border-bottom: 1px solid #ddd; 
                       vertical-align: top; word-wrap: break-word; max-width: 600px;}
                th {color: #ff0000; font-weight: bold; font-size: 16px; background-color: #f5f5f5;}
                td {color: #0000ff; font-size: 14px;}
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

            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            cost_prompt = prompt_tokens * 0.03 / 1000
            cost_completion = completion_tokens * 0.06 / 1000
            cost_total = cost_prompt + cost_completion

            df_token_cost = pd.DataFrame({
                "In Tokens (Prompt)": [prompt_tokens],
                "Out Tokens (Completion)": [completion_tokens],
                "Total Tokens": [total_tokens],
                "Cost (USD)": [f"{cost_total:.4f}"]
            })
            st.subheader("API Token Usage and Cost")
            st.table(df_token_cost)

if __name__ == "__main__":
    main()
