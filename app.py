# =======================================================================
# File: app.py
#
# Purpose:
#   Main Streamlit application file for the AI-BOL-POC-GPT4oMini project.
#
# Role:
#   - Handles file upload for a PDF.
#   - Processes text-based pages with pdfplumber and calls GPT-4o-mini for final extraction (unchanged).
#   - If a page has no text, calls GPT-4 for image extraction, accumulating usage and cost.
#   - Combines text from all pages and displays the final structured data with your original styling.
#   - Shows separate usage/cost lines for GPT-4o-mini (text-based) and GPT-4 (image-based).
#
# Note:
#   - This code reverts text-based logic and styling to exactly what you had in your attached version.
#   - Tesseract OCR is disabled.
# =======================================================================

import streamlit as st
import requests
import pandas as pd
import openai
import json
import pdfplumber
# import pytesseract  # OCR is disabled
from PIL import Image
from io import BytesIO
import base64

# Hide unnecessary Streamlit UI elements (same as your attached version)
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
    Retrieves the GPT-4o-mini API key from Streamlit secrets.
    Must be stored in .streamlit/secrets.toml under 'api-key-gpt-4o-mini'.
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
    If a page has no extractable text, we skip OCR (disabled).
    Returns concatenated text from all pages or an empty string if none is found.
    (Text-based code remains exactly as in your attached version.)
    """
    text = ""
    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            if not pdf.pages:
                st.error("No pages found in the PDF.")
                return ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    st.info("No text detected on a page; OCR fallback is disabled.")
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return ""
    return text.strip()

def call_gpt4o_mini_text_api(pdf_text, api_key):
    """
    Sends the combined PDF text to GPT-4o-mini for structured data extraction.
    (Unchanged text-based logic from your attached version.)
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
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an assistant that processes Bill of Lading text and returns structured JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=3000
        )
        return response
    except openai.error.OpenAIError as oe:
        st.error(f"OpenAI API error (text-based): {oe}")
        return None

def call_gpt4_image_api(image, page_index, api_key):
    """
    Calls GPT-4 to extract text from a scanned page image.
    Returns (extracted_text, usage_dict).
    """
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_bytes = buffered.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    data_uri = "data:image/jpeg;base64," + img_base64

    payload = {
        "model": "gpt-4o",  # GPT-4
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_uri
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            f"This is a scanned page of a Bill of Lading document (page {page_index}). "
                            "Return the entire text exactly as it appears, including punctuation, line breaks, and spacing, "
                            "without summarizing or omitting any details."
                        )
                    }
                ]
            }
        ],
        "temperature": 0,
        "max_tokens": 3000
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    try:
        resp = requests.post("https://api.openai.com/v1/chat/completions",
                             headers=headers, data=json.dumps(payload))
        if resp.status_code != 200:
            st.error(f"OpenAI Image API error (page {page_index}): {resp.text}")
            return "", {}
        resp_json = resp.json()
        text_result = resp_json["choices"][0]["message"]["content"].strip()
        usage = resp_json.get("usage", {})
        return text_result, usage
    except Exception as e:
        st.error(f"Error calling GPT-4 image API on page {page_index}: {e}")
        return "", {}

def extract_text_from_pdf_with_image_fallback(file_bytes, api_key):
    """
    For each page:
      - If text is found by pdfplumber, use it.
      - Else call GPT-4 for image extraction, accumulate usage tokens.
    Returns (combined_text, usage dict for image-based calls).
    """
    full_text = ""
    cumulative_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            if not pdf.pages:
                st.error("No pages found in the PDF.")
                return "", cumulative_usage
            for i, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    full_text += page_text + "\n"
                else:
                    st.info(f"No text detected on page {i}; using image-based extraction.")
                    page_image = page.to_image(resolution=300).original
                    extracted, usage = call_gpt4_image_api(page_image, i, api_key)
                    full_text += extracted + "\n"
                    for k in cumulative_usage:
                        cumulative_usage[k] += usage.get(k, 0)
        return full_text.strip(), cumulative_usage
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return "", cumulative_usage

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

            # 1) Combine text from pdfplumber or GPT-4 fallback
            combined_text, image_usage = extract_text_from_pdf_with_image_fallback(file_bytes, api_key)
            if not combined_text:
                st.warning("No text could be extracted from the PDF.")
                return

            # 2) Call GPT-4o-mini for structured extraction (unchanged text-based approach)
            response = call_gpt4o_mini_text_api(combined_text, api_key)
            if response is None:
                return

            try:
                message_content = response["choices"][0]["message"]["content"]
                prediction = json.loads(message_content)
            except (KeyError, json.JSONDecodeError) as e:
                st.error(f"Failed to decode JSON from API response: {e}")
                st.text("Raw response:")
                st.text(json.dumps(response, indent=2))
                return

            # 3) Build the colored tables exactly as in your “second image”
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

            # 4) Display cost for GPT-4o-mini (text-based) and GPT-4 (image fallback)
            st.subheader("API Token Usage and Cost")

            # ---- GPT-4o-mini usage (final text-based extraction) ----
            text_usage = response.get("usage", {})
            prompt_tokens = text_usage.get("prompt_tokens", 0)
            completion_tokens = text_usage.get("completion_tokens", 0)
            total_tokens = text_usage.get("total_tokens", 0)
            # cost logic as from your second image
            cost_prompt_cents = (prompt_tokens / 1e6) * 0.15 * 100
            cost_completion_cents = (completion_tokens / 1e6) * 0.60 * 100
            cost_total_cents = cost_prompt_cents + cost_completion_cents

            # Build the table for GPT-4o-mini usage
            df_token_cost = pd.DataFrame({
                "In Tokens (Prompt)": [prompt_tokens],
                "Out Tokens (Completion)": [completion_tokens],
                "Total Tokens": [total_tokens],
                "Cost (cents)": [f"{cost_total_cents:.2f}"]
            })
            df_token_cost.index = ["" for _ in range(len(df_token_cost))]
            styled_table = df_token_cost.style.set_properties(**{'text-align': 'left'}).to_html()

            st.markdown("**Text-based Extraction (GPT-4o-mini)**")
            st.markdown(styled_table, unsafe_allow_html=True)

            # ---- GPT-4 usage for image fallback ----
            image_prompt_tokens = image_usage.get("prompt_tokens", 0)
            image_completion_tokens = image_usage.get("completion_tokens", 0)
            image_total_tokens = image_usage.get("total_tokens", 0)
            # cost for GPT-4 image fallback: 0.03 $/1K prompt => 0.003 cents/token
            #                                  0.06 $/1K completion => 0.006 cents/token
            image_cost_cents = (image_prompt_tokens * 0.003) + (image_completion_tokens * 0.006)

            # If we never used GPT-4 fallback, these tokens are zero => cost is zero
            st.markdown("**Image-based Extraction (GPT-4)**")
            df_image_cost = pd.DataFrame({
                "In Tokens (Prompt)": [image_prompt_tokens],
                "Out Tokens (Completion)": [image_completion_tokens],
                "Total Tokens": [image_total_tokens],
                "Cost (cents)": [f"{image_cost_cents:.2f}"]
            })
            df_image_cost.index = ["" for _ in range(len(df_image_cost))]
            styled_image_table = df_image_cost.style.set_properties(**{'text-align': 'left'}).to_html()
            st.markdown(styled_image_table, unsafe_allow_html=True)

            # Sum total cost
            combined_cost = cost_total_cents + image_cost_cents
            st.markdown(f"**Total Combined Estimated Cost:** {combined_cost:.2f} cents")


if __name__ == "__main__":
    main()
