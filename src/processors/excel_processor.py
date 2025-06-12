import logging
import os
import glob
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import time
from .table_chunk import TableChunk

logger = logging.getLogger(__name__)

class ExcelProcessor:
    def __init__(self):
        self.table_chunk = TableChunk()

    def process_tables(self):
        try:
            html_files = self.html_processor()
            if not html_files:
                logger.warning("No HTML files found to process.")
                return {"status": "success", "message": "No HTML files to process"}

            for html_file in html_files:
                try:
                    notification_id = os.path.basename(html_file).replace('.html', '')
                    logger.info(f"Processing notification: {notification_id}")
                            
                    html_content = self.get_data_from_html(html_file)
                    if html_content:
                        self.extract_table_data(html_content, notification_id)
                        self.table_chunk.process_table_chunks()
                except Exception as e:
                    logger.error(f"{html_file} processing error: {e}")
                    continue

            return {"status": "success", "message": "Excel processing completed"}
        except Exception as e:
            logger.error(f"Excel processing error: {e}")
            return {"status": "error", "message": str(e)}

    def html_processor(self):
        try:
            html_files = glob.glob('notification_htmls/*.html')
            html_files.sort(key=lambda x: int(os.path.basename(x).replace('.html', '')))
            return html_files
        except Exception as e:
            logger.error(f"HTML processor error: {e}")
            return []

    def get_data_from_html(self, html_file):
        if not os.path.exists(html_file):
            logger.error(f"HTML file not found: {html_file}")
            return None
        with open(html_file, 'r', encoding='utf-8') as file:
            return file.read()

    def is_complex_table(self, table):
        for row in table.find_all('tr'):
            for cell in row.find_all(['td', 'th']):
                colspan = cell.get('colspan')
                rowspan = cell.get('rowspan')
                if colspan and (colspan.strip() == "0" or int(colspan.strip()) > 3):
                    return True
                if rowspan and (rowspan.strip() == "0" or int(rowspan.strip()) > 3):
                    return True
        return False

    def process_table_data(self, table_data, notification_id, table_count):
        try:
            if not table_data:
                return
                
            df = pd.DataFrame(table_data)
            temp_file = f'notification_htmls/{notification_id}_tab_{table_count}.xlsx'
            
            for col in df.columns:
                df[col] = df[col].astype(str)
                
            df.to_excel(temp_file, index=False, engine="openpyxl")
            time.sleep(0.1)  
            if not os.path.exists(temp_file):
                logger.warning("Retrying file check after delay...")
                time.sleep(0.3)  
                if not os.path.exists(temp_file):
                    logger.error(f"Temporary file creation error: {temp_file}")
                    return
                
            df = pd.read_excel(temp_file)
            
            if df.shape[0] < 3:
                os.remove(temp_file)
                return
                
            same_mask = df[df.columns[1]] == df[df.columns[3]]
            df.loc[same_mask, df.columns[3]] = pd.NA
            
            df = df.drop_duplicates(subset=[df.columns[1], df.columns[2]], keep='first')
            
            col1_non_empty = df.iloc[:, 1].notna() & (df.iloc[:, 1] != "")
            other_cols = df.drop(df.columns[1], axis=1)
            other_cols_empty_or_nan = other_cols.apply(lambda col: col.map(lambda x: pd.isna(x) or x == ""))
            only_col1_has_data = col1_non_empty & other_cols_empty_or_nan.all(axis=1)
            df = df[~only_col1_has_data] 
            
            if df.shape[0] > 4:
                df = self.process_tc_fc_data(df)
                df = self.process_header(df)
                
                df = df.astype(str)
                
                df = df.replace({
                    "nan": "",
                    "<NA>": "",
                    "None": "",
                    "NaN": "",
                    "NaT": ""
                })
                
                for idx in df.index:
                    row_values = df.iloc[idx].values  
                    non_empty_values = [val for val in row_values if val and val.strip() and val.lower() not in ["nan", "<na>", "none", "nat"]] 
                    padded_values = non_empty_values + [""] * (len(row_values) - len(non_empty_values))  
                    df.iloc[idx] = padded_values
                df = df.loc[:, (df != "").any(axis=0)]
                final_file = f'notification_htmls/{notification_id}_table_{table_count}.xlsx'
                df.to_excel(final_file, index=False)
            else:
                os.remove(temp_file)
                return
                
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(f'notification_htmls/{notification_id}.html'):
                os.remove(f'notification_htmls/{notification_id}.html')
            
        except Exception as e:
            logger.error(f"Table processing error: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def process_tc_fc_data(self, df):
        try:
            df = df.astype(str)
            
            row_values = df.iloc[2].values
            shifted_values = np.concatenate((["", "", "", "", ""], row_values[:-5]))
            shifted_values = shifted_values.astype(str)  
            df.iloc[2] = shifted_values
            
            tc_fc_exists = any(str(val).strip() in ["TC", "FC", "Total"] 
                            for val in df.iloc[3].values if pd.notna(val))

            if tc_fc_exists:
                tc_fc_row_idx = 3
                info_row_idx = 2
                
                second_info = str(df.iloc[info_row_idx, 6]) if pd.notna(df.iloc[info_row_idx, 6]) else ""
                third_info = str(df.iloc[info_row_idx, 7]) if pd.notna(df.iloc[info_row_idx, 7]) else ""
                
                for col in range(df.shape[1]):
                    value = str(df.iloc[tc_fc_row_idx, col]).strip()
                    if value in ["TC", "FC", "Total"]:
                        if col < 4:  
                            df.iloc[tc_fc_row_idx, col] = f"{value}({second_info})"
                        else:        
                            df.iloc[tc_fc_row_idx, col] = f"{value}({third_info})"
                shifted_values = np.concatenate((["", "", "", "", ""], df.iloc[3].values[:-5]))
                shifted_values = shifted_values.astype(str) 
                df.iloc[3] = shifted_values         
                df = df.drop(index=info_row_idx).reset_index(drop=True)
            return df

        except Exception as e:
            logger.error(f"TC/FC data processing error: {e}")
            return df

    def process_header(self, df):
        try:
            for col in range(df.shape[1]):
                header_note = str(df.iloc[2, col]).strip()
                if header_note and header_note.lower() != "nan":
                    for row in range(3, df.shape[0]):
                        current_value = str(df.iloc[row, col]).strip()
                        if current_value and current_value.lower() != "nan":
                            df.iloc[row, col] = f"{current_value} ({header_note})"

            df = df.drop(index=2).reset_index(drop=True)
            return df

        except Exception as e:
            logger.error(f"Header processing error: {e}")
            return df

    def extract_table_data(self, html, notification_id):
        if not html:
            logger.error(f"HTML content is empty: {notification_id}")
            return
            
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        table_count = 0
        current_table_data = []
        
        for table in tables:
            if self.is_complex_table(table):
                logger.info(f"Complex table.")
                continue
                    
            if 'financial-header-table' in table.get('class', []) and current_table_data:
                self.process_table_data(current_table_data, notification_id, table_count)
                table_count += 1
                current_table_data = []
                
            table_data = []
            rows = table.find_all('tr')
                
            for row in rows:
                cols = []
                for cell in row.find_all(['td', 'th']):
                    if cell.find('div', class_='taxonomy-footnote-value'):
                        continue
                            
                    span = cell.find('span')
                    cell_text = span.get_text(strip=True) if span else cell.get_text(strip=True)
                    cols.append(cell_text or "")
                    
                if cols:
                    table_data.append(cols)
                
            if table_data:
                current_table_data.extend(table_data)
            
        if current_table_data:
            self.process_table_data(current_table_data, notification_id, table_count)
                