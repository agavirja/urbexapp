import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

@st.cache_data(show_spinner=False)
def getuser(token):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata"]
    schema   = 'urbex'
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    df       = pd.read_sql_query(f"""SELECT *  FROM {schema}.users WHERE token='{token}';""" , engine)
    engine.dispose()
    if not df.empty: return True
    else: return False