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
    """Search for similar documents with improved precision"""
    print(f"\n🔍 RAG SEARCH: '{query}'")
    query_embedding = embedding_model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(n_results, 20),
        include=['documents', 'metadatas', 'distances']
    )
    
    # Filter results by relevance threshold
    if results.get('distances') and results['distances'][0]:
        filtered_docs = []
        filtered_distances = []
        filtered_metadatas = []
        
        for i, distance in enumerate(results['distances'][0]):
            if distance < 1.8:
                filtered_docs.append(results['documents'][0][i])
                filtered_distances.append(distance)
                filtered_metadatas.append(results['metadatas'][0][i])
                chunk_preview = results['documents'][0][i][:80].replace('\n', ' ')
                print(f"  ✓ Found chunk from {results['metadatas'][0][i].get('filename', 'unknown')} (distance: {distance:.2f})")
                print(f"    Preview: {chunk_preview}...")
        
        results['documents'] = [filtered_docs]
        results['distances'] = [filtered_distances]
        results['metadatas'] = [filtered_metadatas]
    
    total_chunks = len(results.get('documents', [[]])[0])
    print(f"📊 Retrieved {total_chunks} relevant chunks")
    print(f"⚡ Sending top {min(5, total_chunks)} to LLM\n")
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