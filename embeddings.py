from langchain_huggingface import HuggingFaceEmbeddings

BGE_MODEL = HuggingFaceEmbeddings(
    model_name="BAAI/bge-large-en-v1.5",
    encode_kwargs={
        "normalize_embeddings": True
    }
)