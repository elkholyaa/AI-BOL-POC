import streamlit as st
import requests
from mindee import Client, product, AsyncPredictResponse

# Hide Streamlit UI elements
hide_streamlit_style = """
<style>
.viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_, 
.viewerBadge_link__1S137, .viewerBadge_text__1JaDK {
    display: none !important;
}
.css-1rs6os.edgvbvh3 { display: none !important; }
.stDeployButton { display: none !important; }
.css-16idsys { display: none !important; }
header { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def get_api_key_from_repo():
    """
    Fetches the Mindee API key from a public GitHub repo file.
    Expects a line like: mindee = 'YOUR_API_KEY'
    """
    API_KEY_URL = "https://raw.githubusercontent.com/elkholyaa/api-keys/main/values"
    try:
        response = requests.get(API_KEY_URL)
        if response.status_code == 200:
            lines = response.text.strip().splitlines()
            for line in lines:
                line = line.strip()
                if line.startswith("mindee ="):
                    key_part = line.split("=", 1)[1].strip()
                    key_part = key_part.strip().strip("'").strip('"')
                    return key_part
            st.error("Could not find 'mindee =' line in the values file.")
            return None
        else:
            st.error(f"Error fetching API key from repository: HTTP {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Exception while fetching API key from repository: {e}")
        return None

def extract_text(obj):
    """
    Extracts text from a Mindee prediction field object.
    - For simple fields with 'value' (e.g., bill_of_lading_number), returns the value.
    - For complex fields (e.g., shipper, consignee), formats 'name' and 'address' as in the PDF.
    - Uses <br> for line breaks in Streamlit HTML display.
    """
    if obj is None:
        return "N/A"
    if hasattr(obj, 'value'):
        return str(obj.value).replace("\n", "<br>")
    elif hasattr(obj, 'name') and hasattr(obj, 'address'):
        name = getattr(obj, 'name', '')
        address = getattr(obj, 'address', '')
        if address:
            # Split address by commas and strip whitespace
            address_lines = [line.strip() for line in address.split(',')]
            address_formatted = "<br>".join(address_lines)
        else:
            address_formatted = ""
        # Combine name and address with a line break
        return f"{name}<br>{address_formatted}" if address_formatted else name
    else:
        return str(obj).replace("\n", "<br>")

def main():
    st.markdown(
        "<h1 style='text-align: center; font-family: \"Times New Roman\", serif; color: red;'>شركة خط الحرير</h1>",
        unsafe_allow_html=True
    )

    # Fetch the Mindee API key
    api_key = get_api_key_from_repo()
    if not api_key:
        st.error("Could not retrieve API key from the repository.")
        return

    uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])
    if uploaded_file:
        try:
            with st.spinner("Processing document..."):
                mindee_client = Client(api_key=api_key)
                file_bytes = uploaded_file.read()
                if not file_bytes:
                    st.error("Uploaded file is empty or could not be read.")
                    return

                input_doc = mindee_client.source_from_bytes(file_bytes, uploaded_file.name)
                result: AsyncPredictResponse = mindee_client.enqueue_and_parse(product.BillOfLadingV1, input_doc)

                if result.job.status == "completed" and result.document is not None:
                    prediction = result.document.inference.prediction

                    # Extract data using the updated function
                    data = {
                        "BILL OF LADING No.": extract_text(getattr(prediction, 'bill_of_lading_number', None)),
                        "SHIPPER": extract_text(getattr(prediction, 'shipper', None)),
                        "CONSIGNEE": extract_text(getattr(prediction, 'consignee', None)),
                        "PORT OF LOADING": extract_text(getattr(prediction, 'port_of_loading', None)),
                        "PORT OF DISCHARGE": extract_text(getattr(prediction, 'port_of_discharge', None))
                    }

                    # Create HTML table for display
                    html_table = """
                    <style>
                        table {width: 100%; border-collapse: collapse; margin: 20px 0; background-color: #ffffff; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden;}
                        th, td {padding: 15px; text-align: left; border-bottom: 1px solid #ddd; vertical-align: top; word-wrap: break-word; max-width: 600px;}
                        th {color: #ff0000; font-weight: bold; font-size: 16px; background-color: #f5f5f5;}
                        td {color: #0000ff; font-size: 14px;}
                    </style>
                    <table>
                    <tr>
                    """
                    for field in data.keys():
                        html_table += f"<th>{field}</th>"
                    html_table += "</tr><tr>"
                    for value in data.values():
                        html_table += f"<td>{value}</td>"
                    html_table += "</tr></table>"

                    st.subheader("Parsed Bill of Lading Information")
                    st.markdown(html_table, unsafe_allow_html=True)
                else:
                    error_msg = result.job.error if result.job.error else "Unknown error"
                    st.error(f"Failed to parse document: {error_msg}")
        except Exception as e:
            st.error(f"An error occurred during processing: {e}")

if __name__ == "__main__":
    main()