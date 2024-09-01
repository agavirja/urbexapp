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
        data.index      = range(len(data))
        data['idmerge'] = range(len(data))
        datam           = data[(data['matricula'].notnull()) & (data['chip'].isnull())]
        if not datam.empty:
            datam.drop(columns=['chip'],inplace=True)
            datacopy = datam.copy()
            transformaciones = [
                lambda x: re.sub('[^0-9a-zA-Z]', '', x),
                lambda x: re.sub('[^0-9a-zA-Z]', '', x).lstrip('0'),
                lambda x: re.sub('[^0-9a-zA-Z]', '', x).lstrip('0')[3:],
                lambda x: x.split('-')[-1],
                lambda x: x.replace('-','0'),
                lambda x: x.replace('-','0').lstrip('0'),
                lambda x: x.replace('-','0').lstrip('0')[3:],
                lambda x: procesar_matricula(x),
            ]
            for transformacion in transformaciones:
                datapaso              = datacopy.copy()
                datapaso['matricula'] = datapaso['matricula'].apply(transformacion)
                datam                 = pd.concat([datam, datapaso])
            datam0 = datam.copy()
            datam0['matricula'] = datam0['matricula'].apply(lambda x: '0'+x)
            datam = pd.concat([datam,datam0])
            datam = datam.drop_duplicates(subset=['matricula'],keep='first')
            lista = "','".join(datam['matricula'].astype(str).unique())
            query = f" matriculainmobiliaria IN ('{lista}')"
            data1 = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria as matricula FROM  bigdata.data_bogota_shd_objetocontrato WHERE {query} " , engine)
            data2 = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria as matricula FROM  bigdata.data_bogota_shd_2024 WHERE {query} " , engine)
            datamerge = pd.concat([data1,data2])
            datamerge = datamerge.drop_duplicates(subset='matricula',keep='first')
            datam     = datam.merge(datamerge,on='matricula',how='left',validate='m:1')
            datam     = datam[datam['chip'].notnull()]
            if not datam.empty:
                datam.rename(columns={'chip':'chipn'},inplace=True)
                datam['orderby'] = datam['matricula'].str.len()
                datam = datam.sort_values(by=['idmerge','orderby'],ascending=False)
                datam = datam.drop_duplicates(subset='idmerge',keep='first')
                data  = data.merge(datam[['idmerge','chipn']],on='idmerge',how='left',validate='m:1')
                idd  = (data['chip'].isnull()) & (data['chipn'].notnull())
                if sum(idd)>0:
                    data.loc[idd,'chip'] = data.loc[idd,'chipn']
                data.drop(columns=['chipn','idmerge'],inplace=True)
            
        #---------------------------------------------------------------------#
        # Chip
        datam = data[data['chip'].notnull()]
        if not datam.empty:
            lista = "','".join(datam['chip'].unique())
            query = f" prechip IN ('{lista}')"
            datacatastro = pd.read_sql_query(f"SELECT barmanpre,predirecc,latitud,longitud,prechip as chip,precbarrio as scacodigo, prenbarrio,preaconst,preaterre,prevetustz,preusoph,estrato,precuso,precdestin  FROM  bigdata.data_bogota_catastro WHERE {query}" , engine)
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
             
        #---------------------------------------------------------------------#
        # Formato de Matricula
        datam = data[data['chip'].notnull()]
        if not datam.empty:
            lista = "','".join(datam['chip'].unique())
            query = f" chip IN ('{lista}')"
            data1 = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria as matricula FROM  bigdata.data_bogota_shd_objetocontrato WHERE {query} " , engine)
            data2 = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria as matricula FROM  bigdata.data_bogota_shd_2024 WHERE {query} " , engine)
            datamerge = pd.concat([data1,data2])
            datamerge = datamerge.drop_duplicates(subset='chip',keep='first')
            datamerge.rename(columns={'matricula':'matriculan'},inplace=True)
            datamerge = datamerge[datamerge['matriculan'].notnull()]
            if not datamerge.empty:
                data = data.merge(datamerge,on='chip',how='left',validate='m:1')
                idd  = data['matriculan'].notnull()
                data.loc[idd,'matricula'] = data.loc[idd,'matriculan']
                data.drop(columns=['matriculan'],inplace=True)
        
        for i in ['latitud','longitud','scacodigo','prenbarrio','mpio_ccdgo']:
            if i not in data: data[i] = None
        engine.dispose()
        
    if not data.empty and 'preusoph' in data:
        data['preusoph'] = data['preusoph'].replace(['S','N'],['Si','No'])
        
    return data

def procesar_matricula(matricula):
    try:
        matricula_limpia = re.sub(r'[^a-zA-Z0-9]', '', matricula)
        prefijo          = matricula_limpia[:3]
        resto            = matricula_limpia[3:]
        resto_completo   = resto.zfill(8)
        return prefijo + resto_completo
    except: return matricula
