import streamlit as st
import re
import pandas as pd
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def main(data):
    
    if not data.empty:
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        
        #---------------------------------------------------------------------#
        # Matricula 2 Chip
        data.index = range(len(data))
        datam      = data[(data['matricula'].notnull()) & (data['chip'].isnull())]
        if not datam.empty:
            datam.drop(columns=['chip'],inplace=True)
            datacopy = datam.copy()
            transformaciones = [
                lambda x: re.sub('[^0-9a-zA-Z]', '', x),
                lambda x: re.sub('[^0-9a-zA-Z]', '', x).lstrip('0'),
                lambda x: re.sub('[^0-9a-zA-Z]', '', x).lstrip('0')[3:],
                lambda x: f"0{x.replace('-', '')}",
                lambda x: x.replace('-', ''),
                lambda x: x.split('-')[-1]
            ]
            for transformacion in transformaciones:
                datapaso              = datacopy.copy()
                datapaso['matricula'] = datapaso['matricula'].apply(transformacion)
                datam                 = pd.concat([datam, datapaso])
            datam = datam.drop_duplicates(subset=['matricula'],keep='first')
            
            lista = "','".join(datam['matricula'].astype(str).unique())
            query = f" matriculainmobiliaria IN ('{lista}')"
            data1 = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria as matricula FROM  bigdata.data_bogota_shd_objetocontrato WHERE {query} " , engine)
            data2 = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria as matricula FROM  bigdata.data_bogota_shd_2024 WHERE {query} " , engine)
            datamerge = pd.concat([data1,data2])
            datamerge = datamerge.drop_duplicates(subset='matricula',keep='first')
            datam     = datam.reset_index()
            datam     = datam.merge(datamerge,on='matricula',how='left',validate='m:1')
            datam     = datam[datam['chip'].notnull()]
            datam     = datam.drop_duplicates(subset='index',keep='first')
            if not datam.empty:
                datam.set_index('index', inplace=True)
                datam.rename(columns={'chip':'chipn'},inplace=True)
                datam = datam[['chipn']]
                data = data.merge(datam,how='outer',left_index=True, right_index=True)
                idd  = (data['chip'].isnull()) & (data['chipn'].notnull())
                if sum(idd)>0:
                    data.loc[idd,'chip'] = data.loc[idd,'chipn']
                data.drop(columns=['chipn'],inplace=True)
            
        #---------------------------------------------------------------------#
        # Chip
        datam = data[data['chip'].notnull()]
        if not datam.empty:
            lista = "','".join(datam['chip'].unique())
            query = f" prechip IN ('{lista}')"
            datacatastro = pd.read_sql_query(f"SELECT barmanpre,predirecc,latitud,longitud,prechip as chip,precbarrio as scacodigo, prenbarrio as barrio FROM  bigdata.data_bogota_catastro WHERE {query}" , engine)
            datamerge    = datacatastro.drop_duplicates(subset='chip',keep='first')
            datamerge['mpio_ccdgo'] = '11001'
            data         = data.merge(datamerge,on='chip',how='left',validate='m:1')
            
        #---------------------------------------------------------------------#
        # Matricula
        datam = data[(data['matricula'].isnull()) & (data['chip'].notnull())]
        if not datam.empty:
            lista = "','".join(datam['chip'].unique())
            query = f" chip IN ('{lista}')"
            data1 = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria as matricula FROM  bigdata.data_bogota_shd_objetocontrato WHERE {query} " , engine)
            data2 = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria as matricula FROM  bigdata.data_bogota_shd_2024 WHERE {query} " , engine)
            datamerge = pd.concat([data1,data2])
            datamerge = datamerge.drop_duplicates(subset='chip',keep='first')
            datamerge.rename(columns={'matricula':'matriculan'},inplace=True)
            if not datamerge.empty:
                data = data.merge(datamerge,on='chip',how='left',validate='m:1')
                idd = (data['matriculan'].notnull()) & (data['matricula'].isnull())
                if sum(idd)>0:
                    data.loc[idd,'matricula'] = data.loc[idd,'matriculan']
                data.drop(columns=['matriculan'],inplace=True)
             
        for i in ['latitud','longitud','scacodigo','barrio','localidad','mpio_ccdgo']:
            if i not in data: data[i] = None
        
        engine.dispose()

    return data