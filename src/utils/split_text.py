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

    text = re.sub(r'([.!?])\s+', r'\1\n', text)
    sentences = text.split('\n')
    
    chunks = []
    current_chunk = []
    current_word_count = 0
    last_sentence = None
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sentence_words = sentence.split()
        sentence_word_count = len(sentence_words)
        
        if not current_chunk and last_sentence:
            current_chunk.extend(last_sentence.split())
            current_word_count = len(last_sentence.split())
        
        if current_word_count + sentence_word_count > max_words and current_chunk:
            last_sentence = ' '.join(current_chunk[-sentence_word_count:]) if sentence_word_count < len(current_chunk) else sentence
            
            chunk_text = ' '.join(current_chunk)
            translated_chunk = translate_chunk(chunk_text)
            chunks.append(translated_chunk)
            
            current_chunk = sentence_words
            current_word_count = sentence_word_count
        else:
            current_chunk.extend(sentence_words)
            current_word_count += sentence_word_count
            
        if current_word_count >= min_words and sentence.endswith(('.', '!', '?')):
            last_sentence = sentence
            
            chunk_text = ' '.join(current_chunk)
            translated_chunk = translate_chunk(chunk_text)
            chunks.append(translated_chunk)
            current_chunk = []
            current_word_count = 0
    
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        translated_chunk = translate_chunk(chunk_text)
        chunks.append(translated_chunk)
    
    return chunks
