import re
import json
import pandas as pd

def extract_info_from_filename(filename):
    pattern = r'(\d+)_table_(\d+)_chunk_(\d+)'
    match = re.search(pattern, filename)
    if match:
        return {
            'notification_id': int(match.group(1)),
            'table_num': int(match.group(2)),
            'chunk_index': int(match.group(3))
        }
    return None

def excel_to_json(df):
    records = df.to_dict(orient='records')
    return json.dumps(records, ensure_ascii=False)

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

