from app.tabs.chatbot import chatbot_interface
from streamlit_option_menu import option_menu
from app.tabs.layout_analysis import layout_analysis_interface
import streamlit as st
from PyPDF2 import PdfMerger
import io

st.title("Layout Aware RAG")

# Upload multiple PDFs
pdf_files = st.file_uploader("Upload one or more complex PDF files:", type=["pdf"], accept_multiple_files=True)

def merge_pdfs(files):
    merger = PdfMerger()
    for file in files:
        merger.append(file)
    output_pdf = io.BytesIO()
    merger.write(output_pdf)
    merger.close()
    output_pdf.seek(0)
    return output_pdf

if not pdf_files:
    st.info("Please upload at least one PDF file to continue.")
    st.stop()
import base64

def show_pdf(pdf_file):
    # Convert PDF file (BytesIO or UploadedFile) to base64
    base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
    
    # Embedding PDF in HTML
    pdf_display = f'''
        <iframe 
            src="data:application/pdf;base64,{base64_pdf}" 
            width="100%" 
            height="600" 
            type="application/pdf">
        </iframe>
    '''
    st.components.v1.html(pdf_display, height=620, scrolling=True)

# Merge PDFs into a single file
merged_pdf = merge_pdfs(pdf_files)

# Interface tabs
tabs = ["Layout analysis", "chatbot"]
icons = ["bi-layout-text-window", "person-fill"]

selected_tab = option_menu(
    menu_title="Select a tab",
    options=tabs,
    default_index=0,
    icons=icons,
    orientation="horizontal",
)
st.subheader("📄 Merged PDF Preview")
show_pdf(merged_pdf)

# Important: seek to beginning again for reuse
merged_pdf.seek(0)
# Pass merged PDF as if it were a single file
if selected_tab == "Layout analysis":
    layout_analysis_interface(merged_pdf)
elif selected_tab == "chatbot":
    chatbot_interface(merged_pdf)
