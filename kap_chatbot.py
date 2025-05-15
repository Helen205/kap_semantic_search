import google.generativeai as genai
from config import config
from prompts import prompt as base_prompt
import json
from chromadb.utils import embedding_functions
from client import ClientWrapper
from deep_translator import GoogleTranslator
import time
from chroma_vector import ChromaContent
from chroma_table import ChromaTable

content = ChromaContent()
table = ChromaTable()

class KAPChatbot:
    def __init__(self):
        self.content_collection = self._setup_content_collection()
        self.table_collection = self._setup_table_collection()

    def _setup_content_collection(self):
        client = ClientWrapper().client
        collection_name = content.collection_name
        collection = client.get_collection(
            name=collection_name
        )
        return collection

    def _setup_table_collection(self):
        client = ClientWrapper().client
        collection_name = table.collection_name
        collection = client.get_collection(
            name=collection_name
        )
        return collection

    def translate_to_english(self, text):
        if isinstance(text, dict):
            text = json.dumps(text, ensure_ascii=False)
            
        if not text or not text.strip():
            return text
        try:
            translator = GoogleTranslator(source='tr', target='en')
            return translator.translate(text)
        except Exception:
            return text
        
    def company_search(self, company):
        company_results = self.content_collection.query(
            query_texts=[company],
            n_results=5,
            where={"is_title": True}
        )
        return company_results


    def search_disclosures(self, query, company=None, n_results=5, distance_threshold=0.86, query_type=None):
        query_analysis = self.analyze_query(query)
        english_query = self.translate_to_english(query_analysis)

        if query_type is None:
            query_type = query_analysis.get('query_type', 'general KAP statement')

        is_financial = query_type == 'financial statement'
        is_general = query_type == 'general KAP statement'

        query_results = None

        if company:
            company_results = self.content_collection.query(
                query_texts=[company],
                n_results=5,
                where={"is_title": True}
            )
            
            if not company_results['documents'][0]:
                print(f"Warning: No results found for company '{company}'")
                return {
                    'documents': [],
                    'metadatas': [],
                    'distances': [],
                    'total_results': 0
                }
            filtered_companies = []
            count = 0
            print(f"\nCompanies with {distance_threshold} distance or less:")
            for i, (meta, distance) in enumerate(zip(company_results['metadatas'][0], company_results['distances'][0])):
                if distance < distance_threshold and meta not in filtered_companies:
                    filtered_companies.append(meta)
                    print(f"{i+1}. Title: {meta.get('title')}")
                    print(f"   Distance: {distance:.2f}")
                    count += 1
                    if count == 2:
                        break
                else:
                    filtered_companies.append(meta)
                    print(f"   Title: {meta.get('title')}")
                    print(f"   Distance: {distance:.2f}")
                    count += 1
                    if count == 2:
                        break
            
            notification_ids = [meta.get('notification_id') for meta in filtered_companies]
            
            if is_financial:
                query_results = self.table_collection.query(
                    query_texts=[english_query],
                    n_results=n_results,
                    where={"notification_id": {"$in": notification_ids}}
                )
                for i, meta in enumerate(query_results['metadatas'][0]):
                    notif_id = meta.get('notification_id')
                    for company_meta in filtered_companies:
                        if company_meta.get('notification_id') == notif_id:
                            meta['title'] = company_meta.get('title')
                            break
            elif is_general:
                query_results = self.content_collection.query(
                    query_texts=[english_query],
                    n_results=n_results,
                    where={"notification_id": {"$in": notification_ids}}
                )
        else:
            if is_financial:
                query_results = self.table_collection.query(
                    query_texts=[english_query],
                    n_results=n_results
                )
            elif is_general:
                query_results = self.content_collection.query(
                    query_texts=[english_query],
                    n_results=n_results
                )
        
        if query_results is None:
            return {
                'documents': [],
                'metadatas': [],
                'distances': [],
                'total_results': 0
            }
        
        return query_results

    def format_response(self, results, query, limit=3):
        if not results['documents']:
            return {"error": "No disclosures found for this topic."}

        response_data = {
            "disclosures": []
        }
        
        if isinstance(results['documents'], list) and len(results['documents']) > 0 and isinstance(results['documents'][0], list):
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
        else:
            documents = results['documents']
            metadatas = results['metadatas']

        for i, (doc, metadata) in enumerate(zip(documents, metadatas)):
            if i >= limit:
                break
            try:
                doc = str(doc) if doc else ''
                title = str(metadata.get('title', ''))
                
                if doc.strip() == title.strip():
                    continue
                    
                notification_id = str(metadata.get('notification_id', ''))
                table_num = str(metadata.get('table_num', ''))
                chunk_index = str(metadata.get('chunk_index', ''))
                
                disclosure = {
                    "title": title,
                    "notification_id": notification_id,
                    "table_number": table_num if table_num else None,
                    "chunk_index": chunk_index if chunk_index else None,
                    "content": doc
                }
                
                response_data["disclosures"].append(disclosure)

            except Exception as e:
                print(f"Error formatting response for document {i}: {str(e)}")
                continue

        return response_data
    def clean_json(self, json_str):
        json_str = json_str.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:]
        if json_str.endswith('```'):
            json_str = json_str[:-3]
        return json_str.strip()

    def chat(self, query):
        try:
            try:
                query = self.clean_json(query)
                
                print(f"\nCleaned JSON: {query}")
                query_data = json.loads(query)
                company = query_data.get('args', {}).get('company')
                search_query = query_data.get('args', {}).get('query')
                query_type = query_data.get('query_type')
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {str(e)}")
                company = None
                search_query = query
                query_type = 'general KAP statement'
                print(f"\nNormal query: {query}")

            query_analysis = self.analyze_query(search_query)
            print(f"\nQuery Analysis: {query_analysis}")
            
            results = self.search_disclosures(search_query, company, n_results=5, query_type=query_type)
            response = self.format_response(results, search_query, limit=3)
            gemini_prompt = f"""
                Query: {search_query}
                Answer: {results}
                
                Is this answer relevant to the query? This question is the result of a semantic search and should be evaluated according to whether it is within the answer to the question I asked. Evaluate in Turkish and explain why and give the percentage of accuracy.
                """
            gemini_evaluation = generate_response(gemini_prompt)   
            print(gemini_evaluation)
            
            print(response)
            
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            import traceback
            traceback.print_exc()

    def analyze_query(self, query):
        prompt = f"""
            Analyze the following financial question and the table content provided, and return a structured analysis with the following:
            1. Type of information sought (numerical value / text / date / etc.)
            2. Important keywords 
            3. Required data points or fields from the financial table that must be used in the calculation
            4. Expected answer format
            Question: {query}
            Provide the answer in JSON format:
            {{
                "info_type": "numerical value" or "text" or "date" or "other",
                "keywords": ["key", "words"],
                "required_operations": ["sum", "subtraction"],
                "expected_format": "expected answer format"
            }}
        """
        try:
            response = generate_response(prompt)
            response = self.clean_json(response)
            
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx+1]
                analysis = json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in response")
            
            analysis['info_type'] = analysis.get('info_type', 'text')
            analysis['keywords'] = analysis.get('keywords', [])
            analysis['required_operations'] = analysis.get('required_operations', [])
            analysis['expected_format'] = analysis.get('expected_format', 'text')
            
            return analysis
        except Exception as e:
            print(f"Error in analyze_query: {str(e)}")
            return {
                'info_type': 'text',
                'keywords': [],
                'required_operations': [],
                'expected_format': 'text'
            }


genai.configure(api_key=config.GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def generate_response(user_prompt):
    time.sleep(2.5)
    response = model.generate_content(user_prompt)
    return response.text

def main():
    while True:
        user_query = input("\nEnter your query: ")
        if user_query.lower() == 'q':
            break
        full_prompt = base_prompt.format(query=user_query)
        query = generate_response(full_prompt)
        print(query)
        
        chatbot = KAPChatbot()
        chatbot.chat(query)

if __name__ == "__main__":
    main()
