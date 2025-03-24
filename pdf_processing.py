# pdf_processing.py
"""
Purpose:
    This module handles PDF processing for the AI-BOL-POC application.
    It extracts text from PDFs using pdfplumber and provides OCR fallback 
    by calling functions from the api_services module when text extraction fails.
Role:
    - Provides a single function, extract_text_from_pdf_with_image_fallback, 
      which processes each page of a PDF, using OCR when necessary.
Workflow:
    - Opens the PDF using pdfplumber.
    - For each page, attempts to extract text.
    - If no text is found, calls the appropriate OCR function from api_services based on user selection.
    - Returns the combined text and usage information.
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
    """
    Processes the PDF file:
      - Uses pdfplumber to extract text.
      - If a page has no text, uses the selected OCR method.
    Parameters:
      file_bytes: Byte content of the PDF.
      ocr_choice: The OCR method to use when text extraction fails ("Google Cloud Vision", "GPT-4", or "Mistral OCR").
    Returns:
      A tuple (combined_text, usage_dict, gcv_page_count) where:
         combined_text: The concatenated text from all pages.
         usage_dict: Dictionary tracking API token usage (for GPT-4 image API).
         gcv_page_count: Number of pages processed with Google Cloud Vision.
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
                    # Text successfully extracted using pdfplumber.
                    combined_text += page_text + "\n"
                else:
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
                        api_key = get_api_key()
                        if not api_key:
                            continue
                        gpt_text, usage = call_gpt4_image_api(pil_image, i, api_key)
                        combined_text += gpt_text + "\n"
                        # Accumulate token usage.
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

        return combined_text.strip(), usage_dict, gcv_page_count

    except Exception as e:
        st.error(f"Error processing PDF pages: {e}")
        return "", usage_dict, gcv_page_count
