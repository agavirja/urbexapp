import streamlit as st
import re
import pandas as pd
import random
from datetime import datetime

from functions._principal_propietarios_id import main as _principal_propietarios
from functions.getuso_destino import usosuelo_class

from data._principal_getvehiculos import main as _principal_getvehiculos
from data.tracking import savesearch

from display._principal_generador_leads_masivo import main as generar_html
from display._principal_generador_leads_byid import main as generar_html_particular

def main():

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'data_propertyinfo_masivo':pd.DataFrame(),
               'data_propertyinfo_masivo_shd_actual':pd.DataFrame(),
               'data_propertyinfo_masivo_transacciones':pd.DataFrame(),
               'data_propertyinfo_masivo_transacciones_nal':pd.DataFrame(),
               'data_propertyinfo_masivo_shd_historico':pd.DataFrame(),
               'data_propertyinfo_masivo_vehiculos':pd.DataFrame(),
               'data_propertyinfo_masivo_reporte':False,
               'mapkey':None,
               'token':None,
               'id_consulta':None,
               'favorito':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    #-------------------------------------------------------------------------#
    # Subir data
    col1, col2, col3, col4 = st.columns([1,1,1,1],vertical_alignment='center')
    dataupload = pd.DataFrame()
    with col1:
        with st.spinner('Leyendo información'):
            uploaded_file = st.file_uploader("Subir base de datos") 
            if uploaded_file:
                dataupload = pd.read_excel(uploaded_file)
            
    with col2:
        plantilla = pd.DataFrame({'tipo': ['CC', 'NIT' ,'CE', 'PA'], 'documento': [1020712480,901470030,None,None]})
        download_excel(plantilla,nombre='plantilla',label='Descargar plantilla de datos [ejemplo]')


    if not dataupload.empty:
        # Limpiar nombres de columnas
        dataupload.columns = [re.sub('[^a-zA-Z]', '', x.lower()) for x in list(dataupload) if isinstance(x, str) and x != '']
        if 'documento' in dataupload:
            dataupload              = dataupload[dataupload['documento'].notnull()]
            dataupload['documento'] = dataupload['documento'].astype(int).astype(str)

    #-------------------------------------------------------------------------#
    # Formulario      
    if not dataupload.empty:
        lista = dataupload['documento'].unique()
        lista = [re.sub('[^0-9]', '', str(x)) for x in lista if x]
        if isinstance(lista,list) and lista!=[]:
            with col3:
                if st.button('Buscar'): 
                    st.session_state.data_propertyinfo_masivo , st.session_state.data_propertyinfo_masivo_shd_actual, st.session_state.data_propertyinfo_masivo_transacciones, st.session_state.data_propertyinfo_masivo_transacciones_nal, st.session_state.data_propertyinfo_masivo_shd_historico = _principal_propietarios(grupo=lista)
                    st.session_state.data_propertyinfo_masivo_vehiculos  = _principal_getvehiculos(identificaciones=lista)
                    st.session_state.data_propertyinfo_masivo_reporte    = True
                    # Guardar:
                    inputvar = dataupload.to_dict(orient='records')
                    _,st.session_state.id_consulta = savesearch(st.session_state.token, None, '_comercial_propiedades_by_id_masivo', inputvar)


    st.session_state.data_propertyinfo_masivo = buildata(data_propertyinfo_masivo=st.session_state.data_propertyinfo_masivo, data_propertyinfo_masivo_shd_actual=st.session_state.data_propertyinfo_masivo_shd_actual, data_propertyinfo_masivo_transacciones_nal=st.session_state.data_propertyinfo_masivo_transacciones_nal, data_propertyinfo_masivo_vehiculos=st.session_state.data_propertyinfo_masivo_vehiculos)
    st.dataframe(st.session_state.data_propertyinfo_masivo)
    if st.session_state.data_propertyinfo_masivo_reporte:
        
        with col4:
            download_excel(st.session_state.data_propertyinfo_masivo,nombre='urbex-leads',label='Descargar base de datos de leads')

        htmlrender = generar_html(dataupload=dataupload.copy(), dataresult=st.session_state.data_propertyinfo_masivo.copy(), data_predios=st.session_state.data_propertyinfo_masivo_shd_actual.copy(), data_transacciones=st.session_state.data_propertyinfo_masivo_transacciones.copy())
        st.components.v1.html(htmlrender, height=1000, scrolling=True)
    
        if not st.session_state.data_propertyinfo_masivo.empty:
            col1, col2 = st.columns(2,vertical_alignment='center')
            with col1:
                seleccion_nombre = st.selectbox('Selecciona un registro de la base de datos:',options=sorted(st.session_state.data_propertyinfo_masivo['nombre'].unique()))

            dataresult             = st.session_state.data_propertyinfo_masivo[st.session_state.data_propertyinfo_masivo['nombre']==seleccion_nombre]
            numero                 = dataresult['numero'].iloc[0]
            data_predios           = st.session_state.data_propertyinfo_masivo_shd_actual[st.session_state.data_propertyinfo_masivo_shd_actual['numero'].astype(str).str.contains(numero)] if not  st.session_state.data_propertyinfo_masivo_shd_actual.empty and 'numero' in  st.session_state.data_propertyinfo_masivo_shd_actual else pd.DataFrame()
            data_transacciones     = st.session_state.data_propertyinfo_masivo_transacciones[ st.session_state.data_propertyinfo_masivo_transacciones['numero'].astype(str).str.contains(numero)] if not  st.session_state.data_propertyinfo_masivo_transacciones.empty and 'numero' in  st.session_state.data_propertyinfo_masivo_transacciones else pd.DataFrame()
            data_transacciones_nal = st.session_state.data_propertyinfo_masivo_transacciones_nal[ st.session_state.data_propertyinfo_masivo_transacciones_nal['identificacion'].astype(str).str.contains(numero)] if not st.session_state.data_propertyinfo_masivo_transacciones_nal.empty and 'identificacion' in st.session_state.data_propertyinfo_masivo_transacciones_nal else pd.DataFrame()
            data_vehiculos         = st.session_state.data_propertyinfo_masivo_vehiculos[ st.session_state.data_propertyinfo_masivo_vehiculos['identificacion'].astype(str).str.contains(numero)] if not st.session_state.data_propertyinfo_masivo_vehiculos.empty and 'identificacion' in st.session_state.data_propertyinfo_masivo_vehiculos else pd.DataFrame()
            data_shd_historico     = pd.DataFrame()
            
            htmlrender = generar_html_particular(dataresult=dataresult.copy(), data_predios=data_predios.copy(), data_transacciones=data_transacciones.copy(), data_transacciones_nal=data_transacciones_nal.copy(), data_shd_historico=data_shd_historico.copy(), data_vehiculos=data_vehiculos.copy())
            st.components.v1.html(htmlrender, height=2000, scrolling=True)
            
            
    
    
@st.cache_data(show_spinner=False)
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def download_excel(df,nombre='data_urbex',label="Haz clic aquí para descargar"):
    excel_file = df.to_excel(f'{nombre}.xlsx', index=False)
    with open(f'{nombre}.xlsx', 'rb') as f:
        data = f.read()
    st.download_button(
        label=label,
        data=data,
        file_name=f'{nombre}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
@st.cache_data(show_spinner=False)
def buildata(data_propertyinfo_masivo=pd.DataFrame(),data_propertyinfo_masivo_shd_actual=pd.DataFrame(),data_propertyinfo_masivo_transacciones_nal=pd.DataFrame(), data_propertyinfo_masivo_vehiculos=pd.DataFrame()):
    
    if not data_propertyinfo_masivo.empty and not data_propertyinfo_masivo_shd_actual.empty:
        # Inmuebles activos
        df                 = data_propertyinfo_masivo_shd_actual.copy()
        idd                = (df['tipo']=='NIT') &  (df['numero'].apply(lambda x: len(x)>9))
        datapaso           = df[idd]
        datapaso['numero'] = datapaso['numero'].apply(lambda x: x[0:9])
        df                 = pd.concat([df,datapaso])
        df                 = df.sort_values(by=['tipo','numero','chip','year'],ascending=False)
        df                 = df.drop_duplicates(subset=['tipo','numero','chip'],keep='first')
        df['avaluo_catastral'] = pd.to_numeric(df['avaluo_catastral'],errors='coerce')
        df                 = df.groupby(['tipo','numero','chip']).agg({'avaluo_catastral':'max'}).reset_index()
        df.columns         = ['tipo','numero','chip','avaluo_catastral']
        df                 = df.groupby(['tipo','numero']).agg({'avaluo_catastral':['count','sum','median']}).reset_index()
        df.columns         = ['tipo','numero','predios','valortotal','valorpromedio']
    
        data_propertyinfo_masivo = data_propertyinfo_masivo.merge(df,on=['tipo','numero'],how='left',validate='m:1')

    if not data_propertyinfo_masivo.empty and not data_propertyinfo_masivo_transacciones_nal.empty:

        # Transacciones totales
        df         = data_propertyinfo_masivo_transacciones_nal.copy()
        df         = df.explode('procesos')
        df         = df.apply(lambda x: {**(x['procesos']), 'tipo': x['tipo'], 'numero': x['numero'], 'nir': x['nir']}, axis=1)
        df         = pd.DataFrame(df)
        df.columns = ['formato']
        df         = pd.json_normalize(df['formato'])
        df         = df[df['codigo'].isin(['125','126','164','168','169','0125','0126','0164','0168','0169'])]
    
        idd                = (df['tipo']=='NIT') &  (df['numero'].apply(lambda x: len(x)>9))
        datapaso           = df[idd]
        datapaso['numero'] = datapaso['numero'].apply(lambda x: x[0:9])
        df                 = pd.concat([df,datapaso])
        df                 = df.sort_values(by=['tipo','numero','nir'],ascending=False)
        df                 = df.drop_duplicates(subset=['tipo','numero','nir','docid'],keep='first')
        df['cuantia']      = pd.to_numeric(df['cuantia'],errors='coerce')
        df                 = df.groupby(['tipo','numero','nir','docid']).agg({'cuantia':'max'}).reset_index()
        df.columns         = ['tipo','numero','nir','docid','cuantia']
        df                 = df.groupby(['tipo','numero']).agg({'cuantia':['count','sum']}).reset_index()
        df.columns         = ['tipo','numero','transacciones','valortotaltransacciones']
    
        data_propertyinfo_masivo = data_propertyinfo_masivo.merge(df,on=['tipo','numero'],how='left',validate='m:1')
        
        
    if not data_propertyinfo_masivo.empty and not data_propertyinfo_masivo_vehiculos.empty:

        # Transacciones totales
        df                 = data_propertyinfo_masivo_vehiculos.copy()
        df.rename(columns={'identificacion':'numero'},inplace=True)
        idd                = df['numero'].apply(lambda x: len(x)>9)
        datapaso           = df[idd]
        datapaso['numero'] = datapaso['numero'].apply(lambda x: x[0:9])
        df                 = pd.concat([df,datapaso])
        df['id']           = 1
        df                 = df.groupby('numero')['id'].count().reset_index()
        df.columns         = ['numero','vehiculos']
        
        data_propertyinfo_masivo = data_propertyinfo_masivo.merge(df,on=['numero'],how='left',validate='m:1')

    if not data_propertyinfo_masivo.empty and 'fechaDocumento' in data_propertyinfo_masivo:
        data_propertyinfo_masivo['fechaDocumento'] = pd.to_datetime(data_propertyinfo_masivo['fechaDocumento'], errors='coerce')
        hoy = datetime.now()
        
        data_propertyinfo_masivo['edad'] = data_propertyinfo_masivo.apply(
            lambda x: ((hoy - x['fechaDocumento']).days // 365 + 18) if pd.notnull(x['fechaDocumento'])  and 'tipo' in x and isinstance(x['tipo'],str) and x['tipo']!='' and 'nit' not in x['tipo'].lower() else None, axis=1
        )
        
        
    return data_propertyinfo_masivo