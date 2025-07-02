import time
import ast
import requests
import pandas as pd
import streamlit as st
from PIL import ImageDraw
from surya.settings import settings
import fitz  # PyMuPDF

from app.helpers.layout_analysis import get_page_image, draw_polys_on_image
from app.helpers.db import select_layout_analysis
from app.helpers.openaiApi import retrieve_and_generate

API_URL = "http://127.0.0.1:8000/ask/rag_response"
DATABASE = "application.db"
HIGHLIGHT_COLOR = (225, 225, 0)


# --- Utility Functions ---

def process_page_chunks(data, real_page_number):
    page_label = f"page_{real_page_number}"
    matching_key = next((k for k, v in data["Pages"].items() if v == page_label), None)
    if matching_key is None:
        raise ValueError(f"Page {real_page_number} not found in data['Pages'].")

    chunks = data["Chunks"].get(matching_key, [])
    all_lines = []
    for chunk in chunks:
        for i, line in enumerate(chunk.split('\n')):
            if line.endswith('-') and i + 1 < len(chunks):
                merged = line[:-1] + chunks[i + 1].lstrip()
                if len(merged.split()) >= 4:
                    all_lines.append(merged)
            elif len(line.split()) >= 4:
                all_lines.append(line)
    return all_lines


def highlight_text_on_image(image, pdf_file, page_num, texts_to_highlight, dpi=300):
    pdf_bytes = pdf_file.getvalue()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num - 1]
    draw = ImageDraw.Draw(image, "RGBA")
    scale = dpi / 72

    if isinstance(texts_to_highlight, str):
        texts_to_highlight = [texts_to_highlight]

    for text in texts_to_highlight:
        for rect in page.search_for(text):
            x0, y0, x1, y1 = [int(coord * scale) for coord in rect]
            draw.rectangle([x0, y0, x1, y1], fill=HIGHLIGHT_COLOR + (128,))
    doc.close()
    return image


def find_polys(page, ai_chunks):
    page_id = f"page_{page}"
    if isinstance(ai_chunks, dict):
        ai_chunks = pd.DataFrame(ai_chunks)
    filtered_df = ai_chunks.query("Pages == @page_id")
    layout_df = select_layout_analysis(page_id)

    polys, texts = [], []
    for _, chunk_row in filtered_df.iterrows():
        texts.append(chunk_row['Chunks'][0])
        for i, layout_row in layout_df.iterrows():
            if layout_row['text'] in chunk_row['Chunks'][0] or chunk_row['Chunks'][0] in layout_row['text']:
                polys.append(layout_row['poly'])
                if i > 0:
                    polys.append(layout_df.iloc[i - 1]['poly'])
                if i < len(layout_df) - 1:
                    polys.append(layout_df.iloc[i + 1]['poly'])
    return texts, [ast.literal_eval(p) for p in polys]


def render_sources(images, page_numbers):
    images_per_row = 3
    with st.expander("Related Pages"):
        for i in range(0, len(images), images_per_row):
            remaining = len(images) - i
            num_cols = min(images_per_row, remaining)
            cols = st.columns(num_cols)
            for j in range(num_cols):
                with cols[j]:
                    st.image(images[i + j],caption=f"Page {page_numbers[i + j]}")


# --- Main Chat UI Function ---
def chatbot_interface(in_file):
    

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # --- Show Chat History with Highlighted Pages ---
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["message"], unsafe_allow_html=True)

            if message["role"] == "assistant" and "source_pages" in message and "ai_chunks" in message:
                pages = message["source_pages"]
                ai_chunks = message["ai_chunks"]

                if pages:
                    images, page_text_map = [], {}
                    for page in pages:
                        text_chunks, polygons = find_polys(page, ai_chunks)
                        base_img = get_page_image(in_file, page, dpi=settings.IMAGE_DPI_HIGHRES)
                        search_texts = process_page_chunks(ai_chunks, page)
                        highlighted_img = highlight_text_on_image(
                            base_img.copy(), in_file, page, search_texts, dpi=settings.IMAGE_DPI_HIGHRES
                        )
                        final_img = draw_polys_on_image(polygons, highlighted_img, label_font_size=30)
                        images.append(final_img)
                        page_text_map[page] = text_chunks
                    render_sources(images,pages)

    # --- Handle New User Input ---
    if user_input := st.chat_input("Ask a question about this PDF..."):
        st.session_state.chat_history.append({"role": "user", "message": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer,pages,ai_chunks = retrieve_and_generate(user_input)


            # Format and stream response
            sources_html = (
                "<br><ul><li>" + "</li><li>".join([f"Page {p}" for p in pages]) + "</li></ul>"
                if pages else ""
            )
            full_response = answer + sources_html
            buffer = ""
            display = st.empty()
            for word in full_response.split():
                buffer += " " + word
                time.sleep(0.04)
                display.markdown(buffer + " ▌", unsafe_allow_html=True)
            display.markdown(full_response, unsafe_allow_html=True)

            # Show visual context
            if pages:
                images, page_text_map = [], {}
                for page in pages:
                    text_chunks, polygons = find_polys(page, ai_chunks)
                    base_img = get_page_image(in_file, page, dpi=settings.IMAGE_DPI_HIGHRES)
                    search_texts = process_page_chunks(ai_chunks, page)
                    highlighted_img = highlight_text_on_image(
                        base_img.copy(), in_file, page, search_texts, dpi=settings.IMAGE_DPI_HIGHRES
                    )
                    final_img = draw_polys_on_image(polygons, highlighted_img, label_font_size=30)
                    images.append(final_img)
                    page_text_map[page] = text_chunks
                render_sources(images,pages)

            # Store assistant response + metadata
            st.session_state.chat_history.append({
                "role": "assistant",
                "message": full_response,
                "source_pages": pages,
                "ai_chunks": ai_chunks,
            })
