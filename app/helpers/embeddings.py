import os
from dotenv import load_dotenv
import chromadb
from openai import OpenAI
from chromadb.utils import embedding_functions
import streamlit as st
import shutil

# Load environment
load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")

def clear_chroma_folders(chroma_dir="data/chroma_persistent_storage"):
    chroma_dir = os.path.join("data", "chroma_persistent_storage")
    for item in os.listdir(chroma_dir):
        item_path = os.path.join(chroma_dir, item)
        # Delete folders only, keep files (like chroma.sqlite3)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)

# Load documents from directory
def load_documents_from_directory(directory_path):
    documents = []
    for filename in os.listdir(directory_path):
        if filename.endswith(".md"):
            with open(os.path.join(directory_path, filename), "r", encoding="utf-8") as file:
                documents.append({"id": filename, "text": file.read()})
    return documents

def split_text(text, chunk_size=1000, chunk_overlap=20):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - chunk_overlap
    return chunks

# This function now receives the OpenAI client
def get_openai_embedding(text, openai_client):
    response = openai_client.embeddings.create(input=text, model="text-embedding-3-small")
    embedding = response.data[0].embedding
    return embedding

def spilt_docs():
    directory_path = os.path.join("data", "text_data", "all_pages")
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"❌ Directory '{directory_path}' not found. Run layout analysis first.")

    documents = load_documents_from_directory(directory_path)
    print(f"📄 Loaded {len(documents)} pages")
    # Split text into chunks
    chunked_documents = []
    for doc in documents:
        chunks = split_text(doc['text'])
        for i, chunk in enumerate(chunks):
            chunked_documents.append({"id": f"{doc['id']}_chunk{i+1}", "text": chunk})
    return chunked_documents

def generate_embeddings():
    openai_client = OpenAI(api_key=openai_key)
    chunked_documents =  spilt_docs()
    for doc in chunked_documents:
        doc["embedding"] = get_openai_embedding(doc["text"], openai_client)
        
    return chunked_documents

def insert_embeddings_into_vector_db(chunked_documents):
    # Initialize consistent Chroma and OpenAI clients
    chroma_client = chromadb.PersistentClient(path="./data/chroma_persistent_storage")
    collection_name = "document_qa_collection"
    clear_chroma_folders()
    # Delete old collection (if it exists)
    try:
        chroma_client.delete_collection(name=collection_name)
        print("✅ Deleted previous collection.")
    except Exception as e:
        print(f"⚠️ Could not delete collection: {e}")

    # Initialize embedding function for Chroma
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_key,
        model_name="text-embedding-3-small",
    )

    # Recreate collection with embedding function
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=openai_ef
    )
    
    for doc in chunked_documents:
        collection.upsert(
            ids=[doc["id"]],
            documents=[doc["text"]],
            embeddings=[doc["embedding"]]
        )