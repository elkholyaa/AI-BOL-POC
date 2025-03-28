# pdf_processing.py
"""
Purpose:
    This module handles PDF processing for the AI-BOL-POC application.
    It extracts text from PDFs using pdfplumber and provides OCR fallback 
    by calling functions from the api_services module when text extraction fails.
Role:
    - Provides a single function, extract_text_from_pdf_with_image_fallback, 
      which processes each page of a PDF using pdfplumber or an OCR method.
Workflow:
    - Opens the PDF using pdfplumber.
    - For each page, attempts to extract text.
    - If no text is found, calls the selected OCR function and counts the fallback.
    - Returns the combined text, a dictionary tracking API token usage, the number of pages
      processed using Google Cloud Vision, and the total count of pages that required OCR fallback.
"""

import streamlit as st
import pdfplumber
from io import BytesIO
from api_services import (
    call_google_vision_ocr,
    call_gpt4_image_api,
    call_mistral_ocr,
    get_api_key,
    get_google_vision_api_key,
    get_mistral_ocr_api_key
)

def extract_text_from_pdf_with_image_fallback(file_bytes, ocr_choice):
    combined_text = ""
    usage_dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    gcv_page_count = 0
    ocr_fallback_count = 0

    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            if not pdf.pages:
                st.error("No pages found in the PDF.")
                return "", usage_dict, gcv_page_count, ocr_fallback_count

            for i, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    combined_text += page_text + "\n"
                else:
                    st.info(f"No text detected on page {i}; using {ocr_choice} for OCR.")
                    ocr_fallback_count += 1
                    pil_image = page.to_image(resolution=300).original

                    if ocr_choice == "Google Cloud Vision":
                        gcv_api_key = get_google_vision_api_key()
                        if not gcv_api_key:
                            continue
                        ocr_text = call_google_vision_ocr(pil_image, gcv_api_key)
                        combined_text += ocr_text + "\n"
                        gcv_page_count += 1

                    elif ocr_choice == "GPT-4o":
                        api_key = get_api_key()
                        if not api_key:
                            continue
                        gpt_text, usage = call_gpt4_image_api(pil_image, i, api_key)
                        combined_text += gpt_text + "\n"
                        for k in usage_dict:
                            usage_dict[k] += usage.get(k, 0)

                    elif ocr_choice == "Mistral OCR":
                        mistral_api_key = get_mistral_ocr_api_key()
                        if not mistral_api_key:
                            continue
                        mistral_text = call_mistral_ocr(pil_image, mistral_api_key)
                        combined_text += mistral_text + "\n"
                    else:
                        st.warning(f"Unknown OCR method: {ocr_choice}")
                        continue

        return combined_text.strip(), usage_dict, gcv_page_count, ocr_fallback_count

    except Exception as e:
        st.error(f"Error processing PDF pages: {e}")
        return "", usage_dict, gcv_page_count, ocr_fallback_count
