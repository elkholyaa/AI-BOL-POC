import streamlit as st
import json
import pandas as pd
from pdf_processing import extract_text_from_pdf_with_image_fallback
from api_services import call_gpt4o_mini_text_api, call_gpt4o_text_api, get_api_key

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
        "Select OCR method for pages without text:",
        ("Google Cloud Vision", "GPT-4o", "Mistral OCR"),
        index=0
    )

    # Checkbox to dump the raw extracted text for debugging.
    dump_raw = st.checkbox("Dump extracted text for debugging", value=False)

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
            # The extraction function now returns:
            #   combined_text: the extracted text,
            #   image_usage: for GPT-4o OCR, expected to be a dict with token counts,
            #   gcv_count: token count (or page count) if Google Cloud Vision was used,
            #   ocr_fallback_count: number of pages for which OCR fallback occurred.
            combined_text, image_usage, gcv_count, ocr_fallback_count = extract_text_from_pdf_with_image_fallback(file_bytes, ocr_choice)

        if not combined_text:
            st.warning("No text could be extracted from the PDF (even after OCR).")
            return

        # If the user opts in, display the raw extracted text for inspection.
        if dump_raw:
            st.subheader("Extracted Text Dump")
            st.text_area("Extracted Text", combined_text, height=300)

        # Determine which structured extraction model to use.
        # For text-based PDFs (no OCR fallback), always use GPT-4o-mini.
        if ocr_fallback_count > 0:
            extraction_model = st.radio(
                "Select structured extraction model for OCR fallback:",
                ("GPT-4o", "GPT-4o-mini"),
                index=1  # default to GPT-4o-mini
            )
            if extraction_model == "GPT-4o":
                response = call_gpt4o_text_api(combined_text, api_key)
            else:
                response = call_gpt4o_mini_text_api(combined_text, api_key)
        else:
            extraction_model = "GPT-4o-mini"
            response = call_gpt4o_mini_text_api(combined_text, api_key)

        if not response:
            return

        try:
            message_content = response["choices"][0]["message"]["content"]
            prediction = json.loads(message_content)
        except (KeyError, json.JSONDecodeError) as e:
            st.error(f"Failed to decode JSON from GPT extraction response: {e}")
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

        # -------------------- API Token Usage and Cost Calculation --------------------
        st.subheader("API Token Usage and Cost")

        # Get token usage from the structured extraction API call.
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        # Retrieve cached tokens if provided (for GPT-4o pricing)
        cached_tokens = usage.get("cached_input_tokens", 0)

        # Calculate structured extraction cost.
        if extraction_model == "GPT-4o":
            extraction_cost_prompt_cents = (prompt_tokens / 1_000_000) * 2.50 * 100
            extraction_cost_cached_cents = (cached_tokens / 1_000_000) * 1.25 * 100
            extraction_cost_completion_cents = (completion_tokens / 1_000_000) * 10.00 * 100
            extraction_cost = extraction_cost_prompt_cents + extraction_cost_cached_cents + extraction_cost_completion_cents
            extraction_pricing_info = "GPT-4o"
        else:
            extraction_cost_prompt_cents = (prompt_tokens / 1_000_000) * 0.15 * 100
            extraction_cost_completion_cents = (completion_tokens / 1_000_000) * 0.60 * 100
            extraction_cost = extraction_cost_prompt_cents + extraction_cost_completion_cents
            extraction_pricing_info = "GPT-4o-mini"

        # Calculate OCR cost if OCR fallback occurred.
        ocr_cost = 0
        if ocr_fallback_count > 0:
            if ocr_choice in ("GPT-4o", "GPT-4o-2024-08-06"):
                # For GPT-4o OCR pricing, expect image_usage to be a dict with token details.
                if isinstance(image_usage, dict):
                    ocr_prompt_tokens = image_usage.get("prompt_tokens", 0)
                    ocr_cached_tokens = image_usage.get("cached_input_tokens", 0)
                    ocr_completion_tokens = image_usage.get("completion_tokens", 0)
                else:
                    # Fallback: if image_usage is just a count, assume all as prompt tokens.
                    ocr_prompt_tokens = image_usage
                    ocr_cached_tokens = 0
                    ocr_completion_tokens = 0
                ocr_cost_prompt_cents = (ocr_prompt_tokens / 1_000_000) * 2.50 * 100
                ocr_cost_cached_cents = (ocr_cached_tokens / 1_000_000) * 1.25 * 100
                ocr_cost_completion_cents = (ocr_completion_tokens / 1_000_000) * 10.00 * 100
                ocr_cost = ocr_cost_prompt_cents + ocr_cost_cached_cents + ocr_cost_completion_cents
                ocr_pricing_info = "GPT-4o OCR"
            elif ocr_choice == "Google Cloud Vision":
                # Assume a cost of 10 cents per page.
                ocr_cost = ocr_fallback_count * 10  # in cents
                ocr_pricing_info = "Google Cloud Vision OCR"
            elif ocr_choice == "Mistral OCR":
                # Assume a cost of 5 cents per page.
                ocr_cost = ocr_fallback_count * 5  # in cents
                ocr_pricing_info = "Mistral OCR"
            else:
                st.error(f"Unknown OCR method: {ocr_choice}")
                ocr_pricing_info = "Unknown OCR method"
        else:
            ocr_pricing_info = "No OCR cost (no OCR fallback)"

        total_cost = extraction_cost + ocr_cost

        st.markdown(f"**Structured Extraction Method:** {extraction_pricing_info} (cost based on token usage)")
        st.markdown(f"Structured Extraction Token Cost: {extraction_cost:.2f} cents")
        if ocr_fallback_count > 0:
            st.markdown(f"**OCR Method:** {ocr_pricing_info} (cost based on usage)")
            st.markdown(f"OCR Cost: {ocr_cost:.2f} cents")
        st.markdown(f"**Total API Token Usage and Cost:** {total_cost:.2f} cents")
        # -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
