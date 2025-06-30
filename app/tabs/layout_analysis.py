
from app.helpers.layout_analysis import *

from app.helpers.embeddings import *

client = chromadb.PersistentClient(path="./data/chroma_persistent_storage")
client.get_or_create_collection(name="init_collection")
client = OpenAI(api_key=openai_key)

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

def layout_analysis(page_count,pdf_file):
    layout_analysis = False
    save_path = os.path.join("data", "uploaded.pdf")
    os.makedirs("data", exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(pdf_file.getbuffer())
    reset_table_layout_analyis()
    for i in range(page_count):
        pil_image_highres = get_page_image(pdf_file, i+1, dpi=settings.IMAGE_DPI_HIGHRES)
        layout_img, layout_pred = layout_detection(pil_image_highres, i+1)
        st.image(layout_img, caption="Detected Layout page_"+str(i+1))
    layout_analysis = True
    return layout_analysis

def layout_analysis_interface(pdf_file):
    st.title("Layout analysis")
    page_count = None
    page_count = page_counter(pdf_file)
    pil_image = get_page_image(pdf_file, 1, settings.IMAGE_DPI)
    pil_image_highres = get_page_image(pdf_file, 1, dpi=settings.IMAGE_DPI_HIGHRES)
    if pil_image is None:
        st.stop()
    pages = []
    page_icons = []
    for i in range(page_count):
        pages.append(("page_"+str(i+1)))
        page_icons.append((""))
        
    run_layout_det = st.button("Run Layout Analysis",key="layout_analysis")
    col1, col2 = st.columns([.5, .5])
    with col1:
        for i in range(page_count):
            pil_image_highres = get_page_image(pdf_file, i+1, dpi=settings.IMAGE_DPI_HIGHRES)
            st.image(pil_image_highres, caption="Uploaded Image")
    with col2:
        layout_analysis_flag = False
        if run_layout_det:  
            empty_directory('./data/', skip_dirs=["chroma_persistent_storage"])
            layout_analysis_flag = layout_analysis(page_count,pdf_file)
            st.write(layout_analysis_flag)
            with st.expander("creating embeddings"):
                create_embeddings()