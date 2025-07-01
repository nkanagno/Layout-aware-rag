
from app.helpers.layout_analysis import *
import time
from app.helpers.embeddings import *

DATABASE = 'application.db'



def reset_table_layout_analyis():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS layout_analysis")
        conn.commit()
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS layout_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                label TEXT,
                page TEXT,
                poly TEXT
            )''')
        conn.commit()
    print("table was reset successfully")

predictors = load_predictors_cached()

def layout_analysis(page_count, pdf_file):
    empty_directory('./data/', skip_dirs=["chroma_persistent_storage"])
    save_path = os.path.join("data", "uploaded.pdf")
    os.makedirs("data", exist_ok=True)

    with st.spinner("Saving PDF and resetting layout analysis table..."):
        with open(save_path, "wb") as f:
            f.write(pdf_file.getbuffer())
        reset_table_layout_analyis()
    
    for i in range(page_count):
        with st.spinner(f"Layout analysis on page {i+1} out of {page_count}..."):
            pil_image_highres = get_page_image(pdf_file, i + 1, dpi=settings.IMAGE_DPI_HIGHRES)
            _, _ = layout_detection(pil_image_highres, i + 1)
    with st.spinner("Generating embeddings..."):
        chunked_documents = generate_embeddings()
        
    with st.spinner("Inserting embeddings to vector db..."):
        insert_embeddings_into_vector_db(chunked_documents)  

def layout_analysis_interface(pdf_file):
    page_count = page_counter(pdf_file)
    pages = []
    for i in range(page_count):
        pages.append(("page_"+str(i+1)))
    if st.button("Analyze PDF", key="analyze_pdf_button"):
        layout_analysis(page_count, pdf_file)
        placeholder = st.empty()
        placeholder.success("Layout analysis complete.")
        time.sleep(2)
        placeholder.empty()
        return True
        