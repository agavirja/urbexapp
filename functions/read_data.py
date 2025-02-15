import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from concurrent.futures import ThreadPoolExecutor, as_completed

def create_connection():
    user = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host = st.secrets["host_read_urbex"]
    schema = st.secrets["schema_write_urbex"]
    return create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

def download_data(query, engine):
    with engine.connect() as connection:
        return pd.read_sql_query(text(query), connection)

def execute_query(listagroup, table_name, variables='*', chunk_size=500):
    schema = st.secrets["schema_write_urbex"]
    engine = create_connection()
    
    batches = [listagroup[i:i + chunk_size] for i in range(0, len(listagroup), chunk_size)]
    
    def process_batch(batch):
        lista = ",".join(map(str, batch))
        query = f"""
        SELECT {variables}
        FROM {schema}.{table_name}
        WHERE grupo IN ({lista})
        """
        return download_data(query, engine)
    
    data = pd.DataFrame()
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_batch = {executor.submit(process_batch, batch): batch for batch in batches}
        for future in as_completed(future_to_batch):
            data = pd.concat([data, future.result()])
    
    engine.dispose()
    return data

def execute_listing_code_query(listacode, table_name, variables='*', chunk_size=500):
    schema = st.secrets["schema_write_urbex"]
    engine = create_connection()
    
    batches = [listacode[i:i + chunk_size] for i in range(0, len(listacode), chunk_size)]
    
    def process_batch(batch):
        lista = "','".join(map(str, batch))
        query = f"""
        SELECT {variables}
        FROM {schema}.{table_name}
        WHERE `code` IN ('{lista}')
        """
        return download_data(query, engine)
    
    data = pd.DataFrame()
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_batch = {executor.submit(process_batch, batch): batch for batch in batches}
        for future in as_completed(future_to_batch):
            data = pd.concat([data, future.result()])
    
    engine.dispose()
    return data

def execute_propietarios_query(listagroup, table_name, variables='*', chunk_size=500):
    schema = st.secrets["schema_write_urbex"]
    engine = create_connection()
    
    batches = [listagroup[i:i + chunk_size] for i in range(0, len(listagroup), chunk_size)]
    
    def process_batch(batch):
        lista = "','".join(map(str, batch))
        query = f"""
        SELECT {variables}
        FROM {schema}.{table_name}
        WHERE `numero` IN ('{lista}')
        """
        return download_data(query, engine)
    
    data = pd.DataFrame()
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_batch = {executor.submit(process_batch, batch): batch for batch in batches}
        for future in as_completed(future_to_batch):
            data = pd.concat([data, future.result()])
    
    engine.dispose()
    return data
