import chromadb
from sentence_transformers import SentenceTransformer
import os
from typing import List
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='multiprocessing.resource_tracker')

# Initialize ChromaDB client
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="group_brain")

# Initialize embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def add_documents(texts: List[str], metadatas: List[dict], ids: List[str]):
    """Add documents to vector database"""
    embeddings = embedding_model.encode(texts).tolist()
    collection.add(
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )

def search_documents(query: str, n_results: int = 5):
    """Search for similar documents"""
    query_embedding = embedding_model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results
    )
    return results

def delete_documents_by_file_id(file_id: str):
    """Delete all documents for a specific file"""
    try:
        # Get all documents
        results = collection.get()
        ids_to_delete = []
        
        for chunk_id in results['ids']:
            if chunk_id.startswith(f"{file_id}_"):
                ids_to_delete.append(chunk_id)
        
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
    except Exception as e:
        print(f"Error deleting documents for file {file_id}: {e}")