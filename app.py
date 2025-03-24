# =======================================================================
# File: app.py
#
# Purpose:
#   Main Streamlit application file for the AI-BOL-POC-GPT4oMini project.
#
# Role:
#   - Handles PDF upload (via Streamlit) and text extraction with pdfplumber.
#   - If a page has no text, we call an OCR fallback (Google Vision, GPT-4 image API, or Mistral OCR).
#   - We combine text from all pages into one string and send it to GPT-4o-mini
#     for structured Bill of Lading extraction.
#   - Displays final data in a single set of tables, just like the other OCR methods do.
#
# Workflow:
#   1. User uploads a PDF file.
#   2. We iterate pages with pdfplumber:
#       - If text is found, append it to `combined_text`.
#       - Otherwise, call the selected OCR method to extract text and append that.
#   3. After all pages are processed, we pass `combined_text` to GPT-4o-mini
#      for Bill of Lading field extraction, then display it in tables.
#
# Note:
#   Ensure that API keys for GPT-4o-mini, Google Cloud Vision, and Mistral OCR
#   are defined in .streamlit/secrets.toml.
# =======================================================================

import streamlit as st
import requests
import pandas as pd
import openai
import json
import pdfplumber
from PIL import Image
from io import BytesIO
import base64

# Hide some Streamlit elements
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
    """Retrieve GPT-4o-mini API key from secrets."""
    try:
        return st.secrets["api-key-gpt-4o-mini"]
    except:
        st.error("GPT-4o-mini API key is missing in the secrets.")
        return None

def get_google_vision_api_key():
    """Retrieve Google Cloud Vision API key from secrets."""
    try:
        return st.secrets["api-key-google-vision"]
    except:
        st.error("Google Cloud Vision API key is missing in the secrets.")
        return None

def get_mistral_ocr_api_key():
    """Retrieve Mistral OCR API key from secrets."""
    try:
        return st.secrets["api-key-mistral-ocr"]
    except:
        st.error("Mistral OCR API key is missing in the secrets.")
        return None

def call_gpt4o_mini_text_api(pdf_text, api_key):
    """
    Sends combined PDF text to GPT-4o-mini for Bill of Lading extraction.
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
        f"Text:\n'''{pdf_text}'''"
    )
    openai.api_key = api_key
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an assistant that processes Bill of Lading text and returns structured JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=3000
        )
        return resp
    except openai.error.OpenAIError as e:
        st.error(f"OpenAI error (GPT-4o-mini text-based): {e}")
        return None

def call_gpt4_image_api(image, page_index, api_key):
    """
    Calls GPT-4 to extract text from a scanned page image.
    Returns (extracted_text, usage_dict).
    """
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    data_uri = "data:image/jpeg;base64," + img_b64

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}},
                    {"type": "text", "text": (
                        f"This is a scanned page of a Bill of Lading document (page {page_index}). "
                        "Return the entire text exactly as it appears, including punctuation, line breaks, and spacing."
                    )}
                ]
            }
        ],
        "temperature": 0,
        "max_tokens": 3000
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(payload))
        if resp.status_code != 200:
            st.error(f"GPT-4 Image API error (page {page_index}): {resp.text}")
            return "", {}
        resp_json = resp.json()
        text = resp_json["choices"][0]["message"]["content"].strip()
        usage = resp_json.get("usage", {})
        return text, usage
    except Exception as e:
        st.error(f"Error calling GPT-4 image API on page {page_index}: {e}")
        return "", {}

def call_google_vision_ocr(image, gcv_api_key):
    """Calls Google Cloud Vision API (DOCUMENT_TEXT_DETECTION) for OCR."""
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    payload = {
        "requests": [
            {
                "image": {"content": img_b64},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
            }
        ]
    }
    url = f"https://vision.googleapis.com/v1/images:annotate?key={gcv_api_key}"
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            st.error(f"Google Vision API error: {resp.text}")
            return ""
        resp_json = resp.json()
        annotations = resp_json["responses"][0].get("textAnnotations", [])
        if annotations:
            return annotations[0]["description"].strip()
        else:
            return ""
    except Exception as e:
        st.error(f"Error calling Google Cloud Vision API: {e}")
        return ""

def call_mistral_ocr(image, mistral_api_key):
    """
    Uploads the image to Mistral, retrieves a signed URL, calls the OCR endpoint, and returns the text.
    """
    # 1. Upload
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    files = {'file': ('page.jpg', buffered.getvalue(), 'image/jpeg')}
    upload_resp = requests.post(
        "https://api.mistral.ai/v1/files",
        headers={"Authorization": f"Bearer {mistral_api_key}"},
        files=files,
        data={"purpose": "ocr"}
    )
    if upload_resp.status_code != 200:
        st.error(f"Mistral file upload error: {upload_resp.text}")
        return ""
    file_id = upload_resp.json().get("id", "")
    if not file_id:
        st.error("No file ID returned from Mistral upload.")
        return ""

    # 2. Signed URL
    signed_url = f"https://api.mistral.ai/v1/files/{file_id}/url?expiry=24"
    su_resp = requests.get(signed_url, headers={
        "Authorization": f"Bearer {mistral_api_key}",
        "Accept": "application/json"
    })
    if su_resp.status_code != 200:
        st.error(f"Mistral get signed URL error: {su_resp.text}")
        return ""
    doc_url = su_resp.json().get("url", "")
    if not doc_url:
        st.error("No signed URL returned from Mistral.")
        return ""

    # 3. OCR
    ocr_payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "image_url",
            "image_url": doc_url
        },
        "include_image_base64": True
    }
    ocr_resp = requests.post(
        "https://api.mistral.ai/v1/ocr",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {mistral_api_key}",
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        },
        json=ocr_payload
    )
    if ocr_resp.status_code != 200:
        st.error(f"Mistral OCR error: {ocr_resp.text}")
        return ""
    ocr_json = ocr_resp.json()
    pages = ocr_json.get("pages", [])
    if not pages:
        st.warning("Mistral OCR returned no pages.")
        return ""
    # Typically, there's a "markdown" field
    return pages[0].get("markdown", "")

def extract_text_from_pdf_with_image_fallback(file_bytes, ocr_choice):
    """
    For each page in the PDF:
      - If pdfplumber extracts text, use it.
      - Otherwise, call the selected OCR method:
          * Google Cloud Vision
          * GPT-4 image
          * Mistral OCR
    Combine all text into one string. Return that string plus usage info.
    """
    combined_text = ""
    usage_dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    gcv_page_count = 0

    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            if not pdf.pages:
                st.error("No pages found in the PDF.")
                return "", usage_dict, gcv_page_count

            for i, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    # We have text from pdfplumber
                    combined_text += page_text + "\n"
                else:
                    # We need to do OCR fallback
                    st.info(f"No text detected on page {i}; using {ocr_choice} for OCR.")
                    pil_image = page.to_image(resolution=300).original

                    if ocr_choice == "Google Cloud Vision":
                        gcv_api_key = get_google_vision_api_key()
                        if not gcv_api_key:
                            continue
                        ocr_text = call_google_vision_ocr(pil_image, gcv_api_key)
                        combined_text += ocr_text + "\n"
                        gcv_page_count += 1

                    elif ocr_choice == "GPT-4":
                        # Call GPT-4 image API
                        gpt_text, usage = call_gpt4_image_api(pil_image, i, get_api_key())
                        combined_text += gpt_text + "\n"
                        # Merge usage stats
                        for k in usage_dict:
                            usage_dict[k] += usage.get(k, 0)

                    elif ocr_choice == "Mistral OCR":
                        mistral_api_key = get_mistral_ocr_api_key()
                        if not mistral_api_key:
                            continue
                        mistral_text = call_mistral_ocr(pil_image, mistral_api_key)
                        combined_text += mistral_text + "\n"
                    else:
                        # Should never happen, but just in case
                        st.warning(f"Unknown OCR method: {ocr_choice}")
                        continue

        return combined_text.strip(), usage_dict, gcv_page_count

    except Exception as e:
        st.error(f"Error processing PDF pages: {e}")
        return "", usage_dict, gcv_page_count

def format_field(value):
    """Replace newlines with <br> for HTML display in tables."""
    if value is None:
        return "N/A"
    return str(value).replace("\n", "<br>")

def main():
    st.markdown("<h1 style='text-align: center; color: red;'>شركة خط الحرير</h1>", unsafe_allow_html=True)

    # Let user pick which OCR method to use for image-based fallback
    ocr_choice = st.radio(
        "Select model for image-based processing:",
        ("Google Cloud Vision", "GPT-4", "Mistral OCR"),
        index=0
    )

    api_key = get_api_key()
    if not api_key:
        return

    # Let user upload a PDF
    uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])
    if uploaded_file:
        file_bytes = uploaded_file.read()
        if not file_bytes:
            st.error("Uploaded file is empty or could not be read.")
            return

        # Extract text with fallback
        with st.spinner("Processing PDF..."):
            combined_text, image_usage, gcv_count = extract_text_from_pdf_with_image_fallback(file_bytes, ocr_choice)

        if not combined_text:
            st.warning("No text could be extracted from the PDF (even after OCR).")
            return

        # Now pass the combined_text to GPT-4o-mini for structured extraction
        response = call_gpt4o_mini_text_api(combined_text, api_key)
        if not response:
            return

        # Attempt to parse JSON
        try:
            message_content = response["choices"][0]["message"]["content"]
            prediction = json.loads(message_content)
        except (KeyError, json.JSONDecodeError) as e:
            st.error(f"Failed to decode JSON from GPT-4o-mini response: {e}")
            st.text("Raw response:")
            st.text(json.dumps(response, indent=2))
            return

        # Display the structured data in a table, just like your "desired output" screenshot

        # 1. "Parsed Bill of Lading Information"
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

        # 2. "Details"
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

        # 3. "Container Information"
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

        # 4. "API Token Usage and Cost"
        st.subheader("API Token Usage and Cost")
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        cost_prompt_cents = (prompt_tokens / 1_000_000) * 0.15 * 100
        cost_completion_cents = (completion_tokens / 1_000_000) * 0.60 * 100
        text_cost = cost_prompt_cents + cost_completion_cents

        if ocr_choice == "Google Cloud Vision":
            # For simplicity, let's assume a per-page cost or a free usage for demonstration
            # or you can keep track of how many pages used GCV, etc.
            st.markdown("**Image-based Extraction (Google Cloud Vision)**")
            st.markdown(f"Processed {gcv_count} pages with Google Cloud Vision => 0.00 cents (example)")
            image_cost_cents = 0
        elif ocr_choice == "GPT-4":
            # If we tracked usage for GPT-4 image calls, we could add it here
            st.markdown("**Image-based Extraction (GPT-4)**")
            # We merged usage into `image_usage` earlier
            # but for demonstration, let's skip cost calculation
            image_cost_cents = 0
        else:
            st.markdown("**Image-based Extraction (Mistral OCR)**")
            st.markdown("Cost calculation for Mistral OCR is not implemented. Refer to docs.")
            image_cost_cents = 0

        total_cost = text_cost + image_cost_cents
        st.markdown(f"**Total Combined Estimated Cost:** {total_cost:.2f} cents")

if __name__ == "__main__":
    main()
