import re
import pandas as pd
from deep_translator import GoogleTranslator

def translate_chunk(chunk):
    translator = GoogleTranslator(source='tr', target='en')
    try:
        chunk = chunk.replace('\n', ' ').replace('\r', ' ')
        chunk = ' '.join(chunk.split())  
        if not chunk.strip():
            return chunk
            
        translation = translator.translate(chunk)
              
        return translation
    except Exception as e:
        print(f"Translation error: {e}")
        return chunk

def split_text_into_sentences(text, min_words=300, max_words=320):
    if not text or pd.isna(text):  
        return []

    text = str(text).strip()
    if not text:  
        return []

    text = text.replace('\n', ' ').replace('\r', ' ')
    text = ' '.join(text.split())  

    words = text.split()
    chunks = []
    current_chunk = []
    last_dot_index = -1
    previous_last_two_sentences = []

    i = 0
    while i < len(words):
        current_chunk.append(words[i])

        if words[i].endswith('.'):
            last_dot_index = len(current_chunk)

        if len(current_chunk) >= min_words:
            if last_dot_index != -1:
                sentences = ' '.join(current_chunk[:last_dot_index]).split('.')
                if len(sentences) >= 2:
                    last_two_sentences = [s.strip() + '.' for s in sentences[-2:]]
                    if len(' '.join(last_two_sentences).split()) > 80:
                        last_two_sentences = [last_two_sentences[-1]]
                else:
                    last_two_sentences = [sentences[-1].strip() + '.']
                
                if previous_last_two_sentences:
                    current_chunk = ' '.join(previous_last_two_sentences).split() + current_chunk
                
                chunk = current_chunk[:last_dot_index]
                translated_chunk = translate_chunk(' '.join(chunk))
                chunks.append(translated_chunk)
                
                previous_last_two_sentences = last_two_sentences
                current_chunk = current_chunk[last_dot_index:]
                last_dot_index = -1
            elif len(current_chunk) >= max_words:
                i += 1
                continue

        i += 1

    if current_chunk:
        if previous_last_two_sentences:
            current_chunk = ' '.join(previous_last_two_sentences).split() + current_chunk
        translated_chunk = translate_chunk(' '.join(current_chunk))
        chunks.append(translated_chunk)

    return chunks
