import streamlit as st
import pandas as pd
import geopandas as gpd
import json
import random
import base64
import urllib.parse
from datetime import datetime

from data.tracking import savesearch
from data.getdataBrands import getoptions,getallcountrybrands
from data._principal_caracteristicas import barmanpre2grupo

from display._principal_marcas import main as generar_html

def main(screensize=1920):

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'data_localizador_marcas':pd.DataFrame(),               

               'mapkey':None,
               'token':None,
               'id_consulta':None,
               'favorito':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    if st.session_state.mapkey is None:
        keytime  = datetime.now().strftime('%Y%m%d%H%M%S%f')
        keyvalue = random.randint(10000, 99999)
        st.session_state.mapkey = f'map_{keytime}{keyvalue}'


    #-------------------------------------------------------------------------#
    # Seleccion por tipo 
    col1,col2,col3 = st.columns([0.4,0.3,0.3],vertical_alignment='center')
    
    dataoptions = getoptions()
    idxlabel    = None
    with col1:
        segmento = st.multiselect('Busqueda por:',options=sorted(list(dataoptions['label'].unique())))
        if isinstance(segmento,list) and segmento!=[]:
            idxlabel = list(set(list(dataoptions[dataoptions['label'].isin(segmento)]['idxlabel'].unique())))

    with col2:
        disabled = False if isinstance(idxlabel,list) and idxlabel!=[] else True
        if st.button('Buscar',disabled=disabled):
            _,st.session_state.id_consulta = savesearch(st.session_state.token, None, '_modulo_analisis_marcas', {'tipo':idxlabel})
            st.session_state.data_localizador_marcas = getallcountrybrands(idxlabel=idxlabel)
            st.rerun()
                
    with col3:
        if st.button('Resetear búsqueda'):
            for key,value in formato.items():
                del st.session_state[key]
            st.rerun()
            
    data = st.session_state.data_localizador_marcas.copy()
    
    if not data.empty:
        #---------------------------------------------------------------------#
        # Filtros
        col1,col2 = st.columns([0.2,0.8])
        
        with col1:
            options = list(sorted(data[data['dpto_cnmbr'].notnull()]['dpto_cnmbr'].unique()))
            options = ['Todos']+options
            index   = options.index("BOGOTÁ, D.C.") if "BOGOTÁ, D.C." in options else 0
            departamento = st.selectbox('Departamento:',options=options,index=index)
            if isinstance(departamento,str) and departamento!='' and 'todo' not in departamento.lower():
                data = data[data['dpto_cnmbr']==departamento]
                
            options = list(sorted(data[data['mpio_cnmbr'].notnull()]['mpio_cnmbr'].unique()))
            options = ['Todos']+options
            index   = options.index("BOGOTÁ, D.C.") if "BOGOTÁ, D.C." in options else 0
            ciudad = st.selectbox('Ciudad:',options=options,index=index)
            if isinstance(ciudad,str) and ciudad!='' and 'todo' not in ciudad.lower():
                data = data[data['mpio_cnmbr']==ciudad]
                
            options = list(sorted(data[data['prenbarrio'].notnull()]['prenbarrio'].unique()))
            options = ['Todos']+options
            barrio = st.selectbox('Barrio:',options=options)
            if isinstance(barrio,str) and barrio!='' and 'todo' not in barrio.lower():
                data = data[data['prenbarrio']==barrio]
    
            options = list(sorted(data[data['empresa'].notnull()]['empresa'].unique()))
            options = ['Todos']+options
            empresa = st.selectbox('Marca:',options=options)
            if isinstance(empresa,str) and empresa!='' and 'todo' not in empresa.lower():
                data = data[data['empresa']==empresa]
                
            options = list(sorted(data[data['nombre'].notnull()]['nombre'].unique()))
            options = ['Todos']+options
            nombre = st.selectbox('Nombre:',options=options)
            if isinstance(nombre,str) and nombre!='' and 'todo' not in nombre.lower():
                data = data[data['nombre']==nombre]
                
            options = list(sorted(data[data['direccion'].notnull()]['direccion'].unique()))
            options = ['Todos']+options
            direccion = st.selectbox('Dirección:',options=options)
            if isinstance(direccion,str) and direccion!='' and 'todo' not in direccion.lower():
                data = data[data['direccion']==direccion]
       
        #-------------------------------------------------------------------------#
        # Mapa
        with col2:
            
            latitud,longitud = 4.688002,-74.054444
            if 'latitud' in data and 'longitud' in data:
                latitud  = data['latitud'].mean()
                longitud = data['longitud'].mean()
                
            
            if not data.empty and 'barmanpre' in data:
                datapaso = data[data['barmanpre'].notnull()]
                
                if not datapaso.empty:
                    barmanprelist = list(datapaso['barmanpre'].unique())
                    datamerge     = barmanpre2grupo(barmanpre=barmanprelist)
                    idd           = datamerge['grupo'].notnull()
                    datamerge.loc[idd,'grupo'] = datamerge.loc[idd,'grupo'].astype(int)
                    datamerge     = datamerge.drop_duplicates(subset='barmanpre',keep='first')
                    data          = data.merge(datamerge,on='barmanpre',how='left',validate='m:1')
                    
            htmlrender = generar_html(data=data, latitud=latitud,longitud=longitud)
            st.components.v1.html(htmlrender, height=5000, scrolling=True)
 
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }