from chromadb.utils import embedding_functions
from client import ClientWrapper

embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction()

collection = ClientWrapper().get_collection(
                name="test",
                embedding_function=embedding_function
)
collection.add(
    documents=["lorem ipsum", "doc2", "doc3", "doc4"],
    metadatas=[{"chapter": "3", "verse": "16"}, {"chapter": "3", "verse": "5"}, {"chapter": "29", "verse": "11"}, {"chapter": "29", "verse": "11"}],
    ids=["id1", "id2", "id3", "id4"]
)

print("Documents added successfully!")