import pandas as pd
import os
import re

class KAPLogger:
    def __init__(self, excel_path="./kap_responses_model.xlsx"):
        self.excel_path = excel_path
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self._initialize_excel()
        
    def _initialize_excel(self):
        if not os.path.exists(self.excel_path):
            df = pd.DataFrame(columns=[
                'Soru',
                'Cevap No',
                'Başlık',
                'İçerik',
                'Benzerlik Skoru',
                'Model',
                'Compatibility',
                'Word'
            ])
            df.to_excel(self.excel_path, index=False)
            
    def _parse_response(self, response):
        parts = re.split(r'\n\n', response)
        results = []
        
        for part in parts:
            if not part.strip():
                continue
                
            lines = part.split('\n')
            if len(lines) < 2:
                continue
                
            title = lines[0].strip()
            company = ''
            date = ''
            content = ''
            similarity = ''
            context = []
            compatibility = ''
            word = ''
            
            for line in lines[1:]:
                if line.startswith('   Şirket:'):
                    company = line.replace('   Şirket:', '').strip()
                elif line.startswith('   Tarih:'):
                    date = line.replace('   Tarih:', '').strip()
                elif line.startswith('   Benzerlik Skoru:'):
                    similarity = line.replace('   Benzerlik Skoru:', '').strip()
                elif line.startswith('   -'):
                    context.append(line.replace('   -', '').strip())
                elif line.startswith('   İçerik:'):
                    content = line.replace('   İçerik:', '').strip()
                elif not line.startswith('   İlgili Cümleler:'):
                    content += ' ' + line.strip()
            
            if title and (company or date or content):
                results.append({
                    'title': title,
                    'content': content.strip(),
                    'similarity': similarity,
                    'context': '\n'.join(context),
                    'model': self.model_name,
                    'compatibility': compatibility,
                    'word': word
                })
        
        return results
            
    def log_response(self, question, response, compatibility=None,word=None):
        try:
            df = pd.read_excel(self.excel_path)
            
            results = self._parse_response(response)
            
            
            for i, result in enumerate(results, 1):
                new_record = {
                    'Soru': question,
                    'Cevap No': i,
                    'Başlık': result['title'],
                    'İçerik': result['content'],
                    'Benzerlik Skoru': result['similarity'],
                    'Model': self.model_name,
                    'Compatibility': compatibility,
                    'Word': word
                }
                
                df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
            
            df.to_excel(self.excel_path, index=False)
            return True
            
        except Exception as e:
            print(f"Error logging response: {str(e)}")
            return False 