import os
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

def ensure_directory(directory):
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory ensured: {directory}")
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")
        raise

def get_files_in_directory(directory, extension=None):
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if extension is None or filename.endswith(extension):
                files.append(os.path.join(root, filename))
    return files

def read_csv_file(file_path):
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        df = pd.read_csv(file_path)
        logger.info(f"Successfully read {len(df)} rows from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
        return None

def read_excel_file(file_path):
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        df = pd.read_excel(file_path)
        logger.info(f"Successfully read {len(df)} rows from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error reading Excel file {file_path}: {e}")
        return None

def delete_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"File deleted: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        raise

def get_file_extension(file_path):
    return os.path.splitext(file_path)[1].lower()

def is_valid_file(file_path, allowed_extensions=None):
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
        
    if allowed_extensions:
        extension = get_file_extension(file_path)
        if extension not in allowed_extensions:
            logger.error(f"Invalid file extension: {extension}")
            return False
            
    return True 