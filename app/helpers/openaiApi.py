from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import chromadb
from openai import OpenAI
from chromadb.utils import embedding_functions
import re
import pandas as pd
from fastapi import FastAPI

print("hello")
app = FastAPI()

load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_key, model_name="text-embedding-3-small",
)

# chroma client
chroma_client = chromadb.PersistentClient(path="./data/chroma_persistent_storage")
collection_name = "document_qa_collection"
collection = chroma_client.get_or_create_collection(
    name=collection_name,embedding_function=openai_ef
)

client = OpenAI(api_key=openai_key)

def query_documents(question, n_results=5):
    citations = []
    results = collection.query(query_texts=question, n_results=n_results)
    relevant_chunks = [doc for sublist in results["documents"] for doc in sublist]
    
    for idx,_ in enumerate(results["documents"][0]):
        doc_id = results["ids"][0][idx]
        citations.append(doc_id)

    return relevant_chunks,citations

def construct_advanced_prompt(question, context, citations):
    # Format citations into the context
    formatted_citations = "\n".join(
        f"[Source {citation.replace('_', ' ')}]" for citation in citations
    )
    
    return f"""
    # Retrieval-Augmented Generation (RAG) Prompt

    ## Context Specification
    - Question Domain: Precise Information Retrieval
    - Retrieval Methodology: Semantic Search
    - Citation Requirement: Mandatory

    ## Question
    {question}

    ## Available Knowledge Sources
    {context}

    ## Source Citations
    {formatted_citations}

    ## Response Guidelines
    1. Answer ONLY using provided sources
    2. Cite sources explicitly for each claim
    3. Cite in format: [Source #]
    4. If information is insufficient, state limitations
    5. Maintain academic rigor in response
    6. Keep your answer small and precise
    7. Focus only on important pages

    ## Citation Instruction
    - Directly attribute information to sources
    - Use [Source #] immediately after relevant information
    - Highlight source relevance and confidence
    """
    
def format_chunks(relevant_chunks, citations):
    formatted_chunks = []
    for i in range(len(relevant_chunks)):
        try:
            citation = citations[i] if citations and i < len(citations) else f"Unknown Source {i+1}"
            chunk = relevant_chunks[i] if relevant_chunks and i < len(relevant_chunks) else "No content available"
            clean_citation = str(citation).split('.')[0].strip()
            formatted_chunk = f"[Source {clean_citation}]:\n{chunk}"
            formatted_chunks.append(formatted_chunk)
        
        except Exception as e:
            # Fallback for any unexpected errors
            formatted_chunks.append(f"[Source Error]: Unable to format source {i+1}")
    
    return formatted_chunks

def generate_response(question, formatted_chucks, citations):

    context = "\n\n".join(formatted_chucks)
    prompt = construct_advanced_prompt(question, context, citations)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
    )

    answer = response.choices[0].message.content
    return answer

def chunks_used_by_ai(df,pages):
    ai_pages = ["page_"+str(page) for page in pages]
    filtered_df = df[df['Pages'].isin(ai_pages)]
    grouped_df = filtered_df.groupby('Pages')['Chunks'].apply(list).reset_index()
    return grouped_df
    
    
def retrieve_and_generate(question):
    chunks,citations = query_documents(question)

    extracted_citations = [citation.split('.')[0] for citation in citations]
    formatted_chunks = format_chunks(chunks, citations)
    ai_response = generate_response(question, formatted_chunks, extracted_citations).replace("_"," ")
    # print(ai_response)
    
    # print(chunks)
    matches = re.findall(r'age (\d+)\]', ai_response)

    # Convert matches to a sorted list of unique page numbers
    pages = sorted(set(map(int, matches)))
    # print(chunks)

    df = pd.DataFrame({
        'Chunks': chunks,
        'Pages': extracted_citations
    })

    ai_chunks = chunks_used_by_ai(df,pages)
    
    return ai_response, pages, ai_chunks

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)
class QuestionRequest(BaseModel):
    question: str

@app.post("/ask/rag_response")
async def ask_question(request: QuestionRequest):
    response, pages, chunks = retrieve_and_generate(request.question)
    return {"answer": response, "related_pages": pages, "related_chunks": chunks}

