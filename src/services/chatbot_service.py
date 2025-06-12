import google.generativeai as genai
import logging
from ..core.config import config
from .chroma_content_service import ChromaContentService
from .chroma_table_service import ChromaTableService
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from ..core.client import ClientWrapper
from deep_translator import GoogleTranslator
import time
import json
from ..core.prompts import prompt as prompt_template


logger = logging.getLogger(__name__)

content = ChromaContentService()
table = ChromaTableService()

class KAPChatbot:
    def __init__(self):
        genai.configure(api_key=config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        self.embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self.content_collection = self._setup_content_collection()
        self.table_collection = self._setup_table_collection()

    def _setup_content_collection(self):
        client = ClientWrapper().client
        collection_name = content.collection_name
        collection = client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
        return collection

    def _setup_table_collection(self):
        client = ClientWrapper().client
        collection_name = table.collection_name
        collection = client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_function
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

    def _filter_company_results(self, company_results, distance_threshold):
        if not company_results['documents'][0]:
            return [], []
            
        filtered_companies = []
        filtered_ids = []
        count = 0
        
        print(f"\nCompanies with {distance_threshold} distance or less:")
        for i, (meta, distance) in enumerate(zip(company_results['metadatas'][0], company_results['distances'][0])):
            if distance < distance_threshold and meta not in filtered_companies:
                filtered_companies.append(meta)
                filtered_ids.append(meta.get('notification_id'))
                print(f"{i+1}. Title: {meta.get('title')}")
                print(f"   Distance: {distance:.2f}")
                count += 1
                if count == 3:
                    break
            else:
                filtered_companies.append(meta)
                filtered_ids.append(meta.get('notification_id'))
                print(f"   Title: {meta.get('title')}")
                print(f"   Distance: {distance:.2f}")
                count += 1
                if count == 3:
                    break
                    
        return filtered_companies, filtered_ids

    def _get_titles_for_notifications(self, notification_ids, query_results):
        content_results = self.content_collection.query(
            query_texts=[""],
            n_results=len(notification_ids),
            where={"notification_id": {"$in": notification_ids}}
        )
            
        title_map = {}
        for meta in content_results['metadatas'][0]:
            if meta.get('is_title', False):
                title_map[meta.get('notification_id')] = meta.get('title')
            
        for i, meta in enumerate(query_results['metadatas'][0]):
            notif_id = meta.get('notification_id')
            if notif_id in title_map:
                meta['title'] = title_map[notif_id]
            
        return query_results

    def _get_table_results(self, english_query, notification_ids, n_results):
        where_clause = {"notification_id": {"$in": notification_ids}} if notification_ids else {}
        return self.table_collection.query(
            query_texts=[english_query],
            n_results=n_results,
            where=where_clause
        )

    def _get_content_results(self, english_query, notification_ids, n_results):
        where_clause = {"notification_id": {"$in": notification_ids}} if notification_ids else {}
        return self.content_collection.query(
            query_texts=[english_query],
            n_results=n_results,
            where=where_clause
        )


    def _date_range(self, start_date, end_date, notification_ids):
        where_clause = {"notification_id": {"$in": notification_ids}} if notification_ids else {}
        results = self.content_collection.query(
            query_texts=[""],
            n_results=len(notification_ids),
            where=where_clause
        )
        
        filtered_results = {
            'documents': [],
            'metadatas': [],
            'distances': []
        }
        
        for i, metadata in enumerate(results['metadatas'][0]):
            history_date = metadata.get('history')
            if history_date and start_date <= history_date <= end_date:
                filtered_results['documents'].append(results['documents'][0][i])
                filtered_results['metadatas'].append(metadata)
                filtered_results['distances'].append(results['distances'][0][i])
        
        return filtered_results

    def _period_range(self, period, notification_ids):
        where_clause = {"notification_id": {"$in": notification_ids}} if notification_ids else {}
        results = self.content_collection.query(
            query_texts=[""],
            n_results=len(notification_ids),
            where=where_clause
        )
        
        if not results or not results.get('metadatas'):
            return None
            
        filtered_results = {
            'documents': [],
            'metadatas': [],
            'distances': []
        }
        
        for i, metadata in enumerate(results['metadatas'][0]):
            if metadata.get('period') == period:
                filtered_results['documents'].append(results['documents'][0][i])
                filtered_results['metadatas'].append(metadata)
                filtered_results['distances'].append(results['distances'][0][i])
        
        return filtered_results

    def search_disclosures(self, response, company=None, n_results=5, distance_threshold=0.86, query_type=None, start_date=None, end_date=None, period=None):
        query_analysis = self.analyze_query(response)
        english_query = self.translate_to_english(query_analysis)

        if query_type is None:
            query_type = query_analysis.get('query_type', 'general KAP statement')

        is_financial = query_type == 'financial statement'
        is_general = query_type == 'general KAP statement'

        query_results = None
        notification_ids = None

        if company:
            company_results = self.content_collection.query(
                query_texts=[company],
                n_results=5,
                where={"is_title": True}
            )
            
            filtered_companies, notification_ids = self._filter_company_results(company_results, distance_threshold)
            logger.info(f"Company search found notification_ids: {notification_ids}")
            
            if not notification_ids:
                logger.warning("No matching companies found")
                return {
                    'documents': [],
                    'metadatas': [],
                    'distances': [],
                    'total_results': 0
                }

        if start_date and end_date and notification_ids:
            date_filtered = self._date_range(start_date, end_date, notification_ids)
            if date_filtered and date_filtered.get('metadatas') and len(date_filtered['metadatas']) > 0:
                notification_ids = [meta.get('notification_id') for meta in date_filtered['metadatas']]
                logger.info(f"Date filtering found notification_ids: {notification_ids}")
            else:
                logger.warning("No results found for the specified date range")
                return {
                    'documents': [],
                    'metadatas': [],
                    'distances': [],
                    'total_results': 0
                }

        if period and notification_ids:
            period_filtered = self._period_range(period, notification_ids)
            if period_filtered and period_filtered.get('metadatas') and len(period_filtered['metadatas']) > 0:
                notification_ids = [meta.get('notification_id') for meta in period_filtered['metadatas']]
                logger.info(f"Period filtering found notification_ids: {notification_ids}")
            else:
                logger.warning("No results found for the specified period")
                return {
                    'documents': [],
                    'metadatas': [],
                    'distances': [],
                    'total_results': 0
                }


        if notification_ids:
            logger.info(f"Final notification_ids before query: {notification_ids}")
            if is_financial:
                query_results = self._get_table_results(english_query, notification_ids, n_results)
                if query_results and query_results.get('metadatas') and len(query_results['metadatas']) > 0:
                    query_results = self._get_titles_for_notifications(notification_ids, query_results)
            elif is_general:
                query_results = self._get_content_results(english_query, notification_ids, n_results)
        else:
            logger.warning("No notification_ids available for final query")
            if is_financial:
                query_results = self._get_table_results(english_query, None, n_results)
                if query_results and query_results.get('metadatas') and len(query_results['metadatas']) > 0:
                    query_results = self._get_titles_for_notifications(
                        [meta.get('notification_id') for meta in query_results['metadatas']],
                        query_results
                    )
            elif is_general:
                query_results = self._get_content_results(english_query, None, n_results)
        
        if query_results is None or not query_results.get('metadatas') or len(query_results['metadatas']) == 0:
            return {
                'documents': [],
                'metadatas': [],
                'distances': [],
                'total_results': 0
            }
        
        return query_results
    def format_response_company(self, results, query, limit=5):
        if not results or not isinstance(results, dict):
            return {"error": "Invalid results format."}

        if not results.get('metadatas'):
            return {"error": "Missing required fields in results."}

        if not results['metadatas']:
            return {"error": "No disclosures found for this topic."}

        response_data = {
            "disclosures": []
        }

        if isinstance(results['metadatas'], list):
            if len(results['metadatas']) > 0 and isinstance(results['metadatas'][0], list):
                metadatas = results['metadatas'][0]
            else:
                metadatas = results['metadatas']
        else:
            metadatas = []

        for i, metadata in enumerate(metadatas):
            if i >= limit:
                break
            title = str(metadata.get('title', ''))
            notification_id = str(metadata.get('notification_id', ''))
            disclosure = {
                "title": title,
                "notification_id": notification_id
                }

            response_data["disclosures"].append(disclosure)

        return response_data

    def format_response(self, results, query, limit=3):
        if not results or not isinstance(results, dict):
            return {"error": "Invalid results format."}

        if not results.get('documents') or not results.get('metadatas'):
            return {"error": "Missing required fields in results."}

        if not results['documents'] or not results['metadatas']:
            return {"error": "No disclosures found for this topic."}

        response_data = {
            "disclosures": []
        }
        
        try:
            if isinstance(results['documents'], list):
                if len(results['documents']) > 0 and isinstance(results['documents'][0], list):
                    documents = results['documents'][0]
                    metadatas = results['metadatas'][0] if len(results['metadatas']) > 0 else []
                else:
                    documents = results['documents']
                    metadatas = results['metadatas']
            else:
                documents = []
                metadatas = []

            if len(documents) != len(metadatas):
                logger.warning(f"Mismatched lengths: documents={len(documents)}, metadatas={len(metadatas)}")
                return {"error": "Data format mismatch."}

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
                    logger.error(f"Error formatting response for document {i}: {str(e)}")
                    continue

            return response_data
            
        except Exception as e:
            logger.error(f"Error in format_response: {str(e)}")
            return {"error": "Error formatting response."}

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
            gemini_evaluation = self.generate_response(gemini_prompt)   
            print(gemini_evaluation)
            
            print(response)
            
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            import traceback
            traceback.print_exc()

    def analyze_query(self, response):
        response = self.generate_response(response)
        response = self.clean_json(response)
            
        try:
            analysis = json.loads(response)
        except json.JSONDecodeError:
            start_idx = response.find('{')
            end_idx = response.rfind('}')
                
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx+1]
                try:
                    analysis = json.loads(json_str)
                except json.JSONDecodeError:
                    logger.error(f"Could not parse JSON from extracted string: {json_str}")
                    raise ValueError("Invalid JSON format in extracted string")
            
        analysis['keywords'] = analysis.get('keywords', [])
        analysis['required_operations'] = analysis.get('required_operations', [])
        analysis['query_type'] = analysis.get('query_type', 'general KAP statement')
            
        logger.info(f"Successfully analyzed query: {analysis}")
        return analysis
            

    def generate_response(self, prompt):
        model = genai.GenerativeModel('gemini-2.0-flash')
        time.sleep(2.5)
        formatted_prompt = prompt_template.format(query=prompt)     
        response = model.generate_content(formatted_prompt)
        return response.text
