import streamlit as st
import pandas as pd
import json
import concurrent.futures
from sqlalchemy import create_engine 
from datetime import datetime

from functions.getuso_destino import getuso_destino,usosuelo_class
from functions.getuso_tipoinmueble import usosuelo2inmueble

from data._principal_caracteristicas import datacaracteristicas
from data._principal_prediales import dataprediales
from data._principal_transacciones import data_anotaciones
from data._principal_propietarios import main as _principal_propietarios
from data.homologar_propietarios import main as homologar_propietarios

@st.cache_data(show_spinner=False)    
def main(grupo=None):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_caracteristicas = executor.submit(datacaracteristicas, grupo=grupo)
        future_prediales       = executor.submit(dataprediales, grupo=grupo, seleccion=0)
        future_dataanotaciones = executor.submit(data_anotaciones, grupo=grupo)
        
        data_general       = future_caracteristicas.result()
        data_prediales     = future_prediales.result()
        data_transacciones_anotaciones = future_dataanotaciones.result()
    
    data_result_predios         = getinfo(data=data_general,item='catastro_predios')
    data_result_usosuelopredios = getinfo(data=data_general,item='catastro_byprecuso')
    data_result_prediales       = getinfopredial(data=data_prediales)
    
    data_transacciones_anotaciones = data_transacciones_anotaciones.to_dict(orient='records') if not data_transacciones_anotaciones.empty else []
    
    # Datos de propietarios: 
    data_result_prediales, data_transacciones_anotaciones, datapropietarios = getpropietarios(data_result_prediales,data_transacciones_anotaciones)

    # Homologar informacion de contactos de propietarios con la ultima informacion a la que se tiene acceso
    data_result_prediales = homologar_propietarios(data_prediales=data_result_prediales, data_anotaciones=data_transacciones_anotaciones, datapropietarios=datapropietarios) 
    
    return data_result_predios, data_result_usosuelopredios, data_result_prediales, data_transacciones_anotaciones, datapropietarios

@st.cache_data(show_spinner=False)     
def getinfo(data=pd.DataFrame(),item=None):
    result = []
    if not data.empty and 'barmanpre' in data and item in data:
        df         = data[['barmanpre',item]]
        df         = df[df[item].notnull()]
        df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df         = df[df[item].notnull()]
        df         = df.explode(item)
        df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre']}, axis=1)
        df         = pd.DataFrame(df)
        df.columns = ['formato']
        df         = pd.json_normalize(df['formato'])
        
        if not df.empty and 'precuso' in df:
            datauso,_ = getuso_destino()
            datauso.rename(columns={'codigo':'precuso','tipo':'usosuelo'},inplace=True)
            datauso   = datauso.drop_duplicates(subset='precuso')
            if 'usosuelo' not in df:
                df = df.merge(datauso[['precuso','usosuelo']],on='precuso',how='left',validate='m:1')
                
        if not df.empty:
            result = df.to_dict(orient='records')
    return result 

@st.cache_data(show_spinner=False)   
def getinfopredial(data=pd.DataFrame()):
    data.index = range(len(data))
    item       = 'prediales' 
    datafinal  = pd.DataFrame()
    if not data.empty and item in data:
        for i in range(len(data)):
            df         = data.iloc[[i]]
            df         = df[['barmanpre',item]]
            df         = df[df[item].notnull()]
            df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df         = df[df[item].notnull()]
            df         = df.explode(item)
            df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre']}, axis=1)
            df         = pd.DataFrame(df)
            df.columns = ['formato']
            df         = pd.json_normalize(df['formato'])
            if not df.empty:
                datafinal  = pd.concat([datafinal,df])
                
    if not datafinal.empty:
        datafinal = datafinal.sort_values(by=['chip','year','url'],ascending=False,na_position='last')
        datafinal = datafinal.drop_duplicates(subset=['chip', 'year', 'direccion', 'matriculainmobiliaria', 'cedula_catastral', 'avaluo_catastral', 'tipo', 'identificacion'],keep='first')
        datafinal = datafinal.sort_values(by=['chip','year'],ascending=False)
    return datafinal.to_dict(orient='records')


@st.cache_data(show_spinner=False)  
def getpropietarios(data_result_prediales,data_transacciones_anotaciones):
    
    try: data_result_prediales = pd.DataFrame(data_result_prediales)
    except: pass
    try: data_transacciones_anotaciones = pd.DataFrame(data_transacciones_anotaciones)
    except: pass

    datapropietarios = pd.DataFrame(columns=['nroIdentificacion', 'tipoPropietario', 'tipoDocumento', 'telefonos', 'email', 'nombre'])
    listaid = []
    try:
        dataid  = pd.DataFrame(data_result_prediales)
        dataid  = dataid[dataid['identificacion'].notnull()].drop_duplicates(subset='identificacion',keep='first')
        listaid += list(dataid['identificacion'].unique())
    except: pass
    try:
        dataidsnr = pd.DataFrame(data_transacciones_anotaciones)
        dataidsnr = dataidsnr[dataidsnr['nrodocumento'].notnull()].drop_duplicates(subset='nrodocumento',keep='first')
        listaid += list(dataidsnr['nrodocumento'].unique())
    except: pass
    if isinstance(listaid,list) and listaid!=[]:
        datapropietarios = _principal_propietarios(numid=listaid)
    
    if not datapropietarios.empty:
        datamergepaso = datapropietarios[datapropietarios['nroIdentificacion'].notnull()].drop_duplicates(subset='nroIdentificacion',keep='first')
        datamergepaso = datamergepaso[['nroIdentificacion', 'tipoPropietario', 'tipoDocumento', 'telefonos', 'email', 'nombre']]
        
        #---------------------------------------------------------------------#
        # Merge con prediales
        datamerge     = datamergepaso.copy()
        datamerge.rename(columns={'nroIdentificacion':'identificacion','nombre':'nombre_new'},inplace=True)
        if not data_result_prediales.empty:
            data_result_prediales = data_result_prediales.merge(datamerge,on='identificacion',how='left',validate='m:1')
            idd = (data_result_prediales['nombre'].isnull()) & (data_result_prediales['nombre_new'].notnull())
            data_result_prediales.loc[idd,'nombre'] = data_result_prediales.loc[idd,'nombre_new'] 
            variables = [x for x in ['nombre_new'] if x in data_result_prediales]
            if variables!=[]:
                data_result_prediales.drop(columns=variables,inplace=True)

        #---------------------------------------------------------------------#
        # Merge con SNR
        datamerge     = datamergepaso.copy()
        datamerge.rename(columns={'nroIdentificacion':'nrodocumento','nombre':'titular_new','email':'email_new'},inplace=True)
        if not data_transacciones_anotaciones.empty:
            data_transacciones_anotaciones = data_transacciones_anotaciones.merge(datamerge,on='nrodocumento',how='left',validate='m:1')
            for i in ['titular','email']:
                if i in data_transacciones_anotaciones: 
                    idd = (data_transacciones_anotaciones[i].isnull()) & (data_transacciones_anotaciones[f"{i}_new"].notnull())
                    data_transacciones_anotaciones.loc[idd,i] = data_transacciones_anotaciones.loc[idd,f"{i}_new"]  
            variables = [x for x in ['titular_new','email_new'] if x in data_transacciones_anotaciones]
            if variables!=[]:
                data_transacciones_anotaciones.drop(columns=variables,inplace=True)
                
    return data_result_prediales, data_transacciones_anotaciones, datapropietarios