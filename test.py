from client import ClientWrapper
import pandas as pd

collection = ClientWrapper().get_or_create_collection(
    name="test"
)

df = pd.read_csv('header_content_processed.csv')
for index, row in df.iterrows():
    try:
        doc_id = f"{row['notification_id']}_{row['chunk_index']}"
        document_text = row['title'] if row['is_title'] else row['content']
                    
        metadata = {
        'title': str(row['title']) if pd.notna(row['title']) else '',
        'content': str(row['content']) if pd.notna(row['content']) else '',
        'is_title': bool(row['is_title']),
        'notification_id': int(row['notification_id']),
        'history': str(row['history']) if pd.notna(row['history']) else '',
        'chunk_index': int(row['chunk_index']),
        'total_chunks': int(row['total_chunks'])
        }
                    
        collection.add(
        documents=[document_text],
        metadatas=[metadata],
        ids=[doc_id]
        )
        print("Documents added successfully!")
    except Exception as e:
        print(f"Error adding documents: {e}")


results = collection.query(
    query_texts=["What is the content of the document?"],
    n_results=5,
)

print("Query results:")
print(results)