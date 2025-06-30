import io, os, json, sqlite3, shutil
import pypdfium2
import streamlit as st
import pytesseract
from PIL import Image
from dotenv import load_dotenv
from surya.models import load_predictors
from surya.layout import LayoutResult
from surya.settings import settings
from surya.debug.draw import draw_polys_on_image
import chromadb
from openai import OpenAI
from chromadb.utils import embedding_functions

# Load environment variables
load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_key)
openai_ef = embedding_functions.OpenAIEmbeddingFunction(api_key=openai_key, model_name="text-embedding-3-small")

# Chroma client
chroma_client = chromadb.PersistentClient(path="./data/chroma_persistent_storage")
collection = chroma_client.get_or_create_collection(name="document_qa_collection", embedding_function=openai_ef)

# Load layout predictors (cached)
@st.cache_resource()
def load_predictors_cached():
    return load_predictors()
predictors = load_predictors_cached()

# --- Directory Utils ---
def create_dirs(page_number, base_dir="text_data"):
    page_dir = os.path.join("data", base_dir, "individual_pages", f"page_{page_number}")
    text_images_dir = os.path.join(page_dir, "text_images")
    os.makedirs(text_images_dir, exist_ok=True)
    return page_dir, text_images_dir

def empty_directory(path, skip_dirs=None):
    skip_dirs = skip_dirs or []
    for item in os.listdir(path):
        if item in skip_dirs:
            continue
        item_path = os.path.join(path, item)
        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.unlink(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

# --- PDF Utils ---
def open_pdf(pdf_file):
    return pypdfium2.PdfDocument(io.BytesIO(pdf_file.getvalue()))

@st.cache_data()
def page_counter(pdf_file):
    doc = open_pdf(pdf_file)
    count = len(doc)
    doc.close()
    return count

@st.cache_data()
def get_page_image(pdf_file, page_num, dpi=settings.IMAGE_DPI):
    doc = open_pdf(pdf_file)
    renderer = doc.render(pypdfium2.PdfBitmap.to_pil, page_indices=[page_num - 1], scale=dpi / 72)
    image = list(renderer)[0].convert("RGB")
    doc.close()
    return image

# --- Core OCR + Storage ---
def insert_into_db(extracted_texts):
    conn = sqlite3.connect('application.db')
    cursor = conn.cursor()
    for item in extracted_texts:
        if all(k in item for k in ("poly", "text", "page", "label")):
            cursor.execute('''
                INSERT INTO layout_analysis (text, label, page, poly)
                VALUES (?, ?, ?, ?)
            ''', (item['text'], item['label'], item['page'], json.dumps(item['poly'])))
    conn.commit()
    conn.close()

def save_texts_to_file(text_blocks, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        for obj in text_blocks:
            if "figure" in obj["label"].lower():
                continue
            if all(x not in obj["label"].lower() for x in ["pagefooter", "picture", "pageheader", "table"]):
                f.write(f"{obj['text']}\n")

def save_page_data(extracted_texts, page_number, base_dir="text_data"):
    page_dir, _ = create_dirs(page_number, base_dir)
    all_pages_path = os.path.join("data", base_dir, "all_pages", f"page_{page_number}.md")
    os.makedirs(os.path.dirname(all_pages_path), exist_ok=True)

    # Save individual and combined markdown files
    save_texts_to_file(extracted_texts, os.path.join(page_dir, f"page_{page_number}.md"))
    save_texts_to_file(extracted_texts, all_pages_path)

    insert_into_db(extracted_texts)


def upscale_image(img, factor=2):
    return img.resize((img.width * factor, img.height * factor), Image.LANCZOS)


def crop_bounding_boxes_from_image(polys, image, labels, page_number, base_dir="text_data"):
    page_dir, image_dir = create_dirs(page_number, base_dir)
    extracted_texts = []

    for i, poly in enumerate(polys):
        x_min, y_min = min(p[0] for p in poly), min(p[1] for p in poly)
        x_max, y_max = max(p[0] for p in poly), max(p[1] for p in poly)
        x_min, x_max = x_min - 10, x_max + 10
        y_min, y_max = (y_min - 4, y_max + 4) if "footnote" not in labels[i].lower() else (y_min, y_max)

        cropped = upscale_image(image.crop((x_min, y_min, x_max, y_max)))
        
        if "figure" not in labels[i].lower():
            config = '--psm 6' if any(x in labels[i].lower() for x in ["equation", "table"]) else ''
            text = pytesseract.image_to_string(cropped, config=config)
            extracted_texts.append({"text": text, "label": labels[i], "poly": poly, "page": f"page_{page_number}"})

        cropped.save(os.path.join(image_dir, f"{labels[i]}.png"))
    save_page_data(extracted_texts, page_number, base_dir)
    return extracted_texts


def layout_detection(img, page_number):
    pred = predictors["layout"]([img])[0]
    polys = [p.polygon for p in pred.bboxes]
    labels = [f"{p.label}-{p.position}-{round(p.top_k[p.label], 2)}" for p in pred.bboxes]
    layout_img = draw_polys_on_image(polys, img.copy(), labels=labels, label_font_size=40)
    crop_bounding_boxes_from_image(polys, img, labels, page_number)
    return layout_img, pred
