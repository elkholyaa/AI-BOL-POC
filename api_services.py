# api_services.py
"""
Purpose:
    This module handles all external API interactions for the AI-BOL-POC application.
    It includes functions to call GPT-4o-mini and GPT-4o for structured Bill of Lading extraction,
    as well as OCR functions using Google Cloud Vision, GPT-4 image API, and Mistral OCR.
Role:
    - Provides API key retrieval functions from Streamlit secrets.
    - Contains functions to communicate with external services, keeping the main app logic clean.
Workflow:
    - The functions in this module are imported and used by pdf_processing.py and app.py.
"""

import streamlit as st
import requests
import openai
import json
import base64
from io import BytesIO
from PIL import Image

def get_api_key():
    """
    Retrieve GPT-4o-mini API key from Streamlit secrets.
    """
    try:
        return st.secrets["api-key-gpt-4o-mini"]
    except KeyError:
        st.error("GPT-4o-mini API key is missing in the secrets.")
        return None

def get_google_vision_api_key():
    """
    Retrieve Google Cloud Vision API key from Streamlit secrets.
    """
    try:
        return st.secrets["api-key-google-vision"]
    except KeyError:
        st.error("Google Cloud Vision API key is missing in the secrets.")
        return None

def get_mistral_ocr_api_key():
    """
    Retrieve Mistral OCR API key from Streamlit secrets.
    """
    try:
        return st.secrets["api-key-mistral-ocr"]
    except KeyError:
        st.error("Mistral OCR API key is missing in the secrets.")
        return None

def call_gpt4o_mini_text_api(pdf_text, api_key):
    """
    Sends the combined PDF text to GPT-4o-mini for structured Bill of Lading extraction.
    Returns the API response.
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
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an assistant that processes Bill of Lading text and returns structured JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=3000
        )
        return response
    except openai.error.OpenAIError as e:
        st.error(f"OpenAI error (GPT-4o-mini text-based): {e}")
        return None

def call_gpt4o_text_api(pdf_text, api_key):
    """
    Sends the combined PDF text to GPT-4o for structured Bill of Lading extraction.
    This function is intended for image-based PDFs when the user selects GPT-4o for extraction.
    Returns the API response.
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
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that processes Bill of Lading text and returns structured JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=3000
        )
        return response
    except openai.error.OpenAIError as e:
        st.error(f"OpenAI error (GPT-4o text-based): {e}")
        return None

def call_gpt4_image_api(image, page_index, api_key):
    """
    Calls GPT-4 image API to extract text from a scanned page image.
    Returns the extracted text and usage information.
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
    """
    Uses Google Cloud Vision API (DOCUMENT_TEXT_DETECTION) to perform OCR on an image.
    Returns the detected text.
    """
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
    Uses Mistral OCR to extract text from an image.
    Returns the concatenated extracted text from all pages.
    """
    # Upload image to Mistral
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

    # Retrieve signed URL
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

    # Perform OCR
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
    # Concatenate text from all pages.
    full_text = ""
    for page in pages:
        full_text += page.get("markdown", "") + "\n"
    return full_text.strip()
