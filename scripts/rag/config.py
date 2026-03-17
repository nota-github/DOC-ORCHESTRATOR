"""RAG pipeline configuration constants."""

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dims, $0.02/1M tokens
CHUNK_SIZE = 800  # tokens
CHUNK_OVERLAP = 100  # tokens
VECTORDB_PATH = "data/vectordb"
COLLECTION_NAME = "confluence_npp02"
TOP_K_CHUNKS = 30  # chunk-level retrieval before page grouping
TOP_K_PAGES = 15  # final page count
CONFLUENCE_SPACE = "NPP02"
EMBEDDING_BATCH_SIZE = 2048  # max texts per API call
