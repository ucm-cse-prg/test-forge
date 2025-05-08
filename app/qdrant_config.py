# mypy: ignore-errors
import io
from fastapi import HTTPException

from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_qdrant import QdrantVectorStore

from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path('.') / 'creds.env'
load_dotenv(dotenv_path=env_path)

qdrant_url = os.getenv("QDRANT_URL")
collection_name = os.getenv("COLLECTION_NAME")
ollama_model = os.getenv("OLLAMA_MODEL")
ollama_url = os.getenv("OLLAMA_URL")

qdrant_client = QdrantClient(url=qdrant_url)
if not qdrant_client.collection_exists(collection_name):
    try:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating collection: {e}")
    
embeddings = OllamaEmbeddings(model=ollama_model, base_url=ollama_url)
vector_store = QdrantVectorStore( #vector store will also be used in actions
    client=qdrant_client,
    collection_name=collection_name,
    embedding=embeddings,
)

llm = OllamaLLM(model=ollama_model, base_url=ollama_url) # going to be used in actions