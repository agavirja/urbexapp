import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import shapely.wkt as wkt
import concurrent.futures
from sqlalchemy import create_engine 
from datetime import datetime

from functions.getuso_destino import getuso_destino,usosuelo_class
from functions.getuso_tipoinmueble import usosuelo2inmueble
from functions.polygonunion import polygonunion

from data._principal_pot import data_pot
from data._principal_caracteristicas import datacaracteristicas
from data._principal_lotes import datalote,lotes_vecinos
from data._principal_proyectos import datacompletaproyectos

from functions._principal_getdatanalisis import main as getradio

#@st.cache_data(show_spinner=False)
def main(grupo=None):
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_datalote       = executor.submit(datalote, grupo=grupo)
        future_pot            = executor.submit(data_pot, grupo=grupo)
        future_terreno        = executor.submit(datacaracteristicas, grupo=grupo,variables='grupo,barmanpre,general_catastro,info_terreno,infopredial')
        future_proyectos      = executor.submit(datacompletaproyectos, grupo=grupo)
        future_transacciones  = executor.submit(getradio, grupo=grupo)
        future_lotesvecinos   = executor.submit(lotes_vecinos, grupo=grupo)

        data_analisis_lote  = future_datalote.result()
        data_analisis_pot   = future_pot.result()
        data_terreno        = future_terreno.result()
        data_proyectos      = future_proyectos.result()
        data_transaciones   = future_transacciones.result()
        data_lotes_completo = future_lotesvecinos.result()
        
    info_pot      = get_pot_general(data_analisis_pot=data_analisis_pot)
    info_pot      = alturamax(info_pot)
    info_terreno  = get_info_terreno(data=data_terreno)
    
    data_lotes          = data_lotes_completo[0]
    data_construcciones = data_lotes_completo[1]
    
    #-------------------------------------------------------------------------#
    # Lat / Lng y Poligono de referencia
    latitud   = data_analisis_lote['latitud'].iloc[0]        if not data_analisis_lote.empty and 'latitud'  in data_analisis_lote and isinstance(data_analisis_lote['latitud'].iloc[0],(float,int)) else None
    longitud  = data_analisis_lote['longitud'].iloc[0]       if not data_analisis_lote.empty and 'longitud' in data_analisis_lote and isinstance(data_analisis_lote['longitud'].iloc[0],(float,int)) else None
    polygon   = wkt.loads(data_analisis_lote['wkt'].iloc[0]) if not data_analisis_lote.empty and 'wkt'      in data_analisis_lote else None
    try:
        if not data_analisis_lote.empty and len(data_analisis_lote)>1:
            latitud      = data_analisis_lote['latitud'].median()  if 'latitud'  in data_analisis_lote else latitud
            longitud     = data_analisis_lote['longitud'].median() if 'longitud' in data_analisis_lote else longitud
            try:
                df          = polygonunion(data_analisis_lote)
                polygon     = wkt.loads(df['wkt'].iloc[0])
            except: polygon = wkt.loads(data_analisis_lote['wkt'].iloc[0])
    except: 
        pass

    #-------------------------------------------------------------------------#
    # Precios de referencia de proyectos nuevos        
    data_proyectos = pricing_proyectos(data_proyectos)
    #-------------------------------------------------------------------------#
    # Precios de referencia de transacciones        
    data_transacciones = pricing_transacciones(grupo=grupo)
    #-------------------------------------------------------------------------#
    # Preciso de referencia
    data_precios_referencia = pd.concat([data_proyectos,data_transacciones])

    return info_pot, info_terreno, latitud, longitud, polygon, data_precios_referencia, data_lotes, data_construcciones
    

@st.cache_data(show_spinner=False)
def get_info_terreno(data=pd.DataFrame()):
    
    datatotal = pd.DataFrame()
    resultado = {'preaconst': None, 'preaterre': None, 'prevetustzmin': None, 'prevetustzmax': None, 'estrato': None, 'predios': None, 'connpisos': None, 'connsotano': None, 'areapolygon': None, 'esquinero': None, 'tipovia': None, 'propietarios': None, 'avaluo_catastral': None, 'impuesto_predial': None, 'avaluomt2terre': None}
    if not data.empty:
        for variable in ['general_catastro','info_terreno','infopredial']:
            df = pd.DataFrame()
            if variable in data:
                df = data[data[variable].notnull()]
            if not df.empty:
                df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
                df           = df[df[variable].notnull()]
                df           = df.explode(variable)
                df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
                df           = pd.DataFrame(df)
                df.columns   = ['formato']
                df           = pd.json_normalize(df['formato'])
                if not df.empty:
                    if not datatotal.empty:
                        datatotal = datatotal.merge(df,on=['grupo','barmanpre'],how='outer')
                    else: 
                        datatotal = df.copy()

    if not datatotal.empty:
        indice = {'preaconst':'sum','preaterre':'sum','prevetustzmin':'min','prevetustzmax':'max','estrato':'max','predios':'sum','connpisos':'max','connsotano':'max',
                  'areapolygon':'sum','esquinero':'max','tipovia':'min','propietarios':'sum','avaluo_catastral':'sum','impuesto_predial':'sum','avaluomt2terre':'max'}
        formato = {}
        for key,value in indice.items():
            if key in datatotal:
                formato.update({key:value})
            
        datatotal['isin'] = 1
        datatotal         = datatotal.groupby('isin').agg(formato).reset_index()
        resultado         = datatotal.to_dict(orient='records')[0]

    return resultado
    

@st.cache_data(show_spinner=False)
def pricing_proyectos(data):
    resultado = pd.DataFrame(columns=['tipo','median','min','max'])
    if not data.empty and 'estado' in data and 'ano' in data:
        data = data[(data['estado'].isin(['Const', 'Prev'])) & (data['ano']==datetime.now().year)]
    if not data.empty and 'tipo' in data:
        resultado = data.groupby(['tipo']).agg({'valormt2':['median','min','max']}).reset_index()
        resultado.columns = ['tipoinmueble','median','min','max']
        resultado['tipo'] = 'Proyectos nuevos'
    return resultado
        
@st.cache_data(show_spinner=False)
def pricing_transacciones(grupo=None):
    
    # Precios de referencia de transacciones
    formato = [
        {'tipoinmueble':'Local','lista':['003','004','006','007','039','040','041','042','094','095']},
        {'tipoinmueble':'Oficina','lista':['015','020','045','080','081','082','092']},
        {'tipoinmueble':'Bodega','lista':['008','025','033','091','093','097']},
        {'tipoinmueble':'Apartamento','lista':['002','038']},
        {'tipoinmueble':'Casa','lista':['001','037']},
        {'tipoinmueble':'Hotel','lista':['021','026','027','046']},
        ]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_transacciones_local = executor.submit(getradio, grupo=grupo , inputvar = {'precuso':['003','004','006','007','039','040','041','042','094','095']})
        data_transaciones_local    = future_transacciones_local.result()

        future_transacciones_oficina = executor.submit(getradio, grupo=grupo , inputvar = {'precuso':['015','020','045','080','081','082','092']})
        data_transaciones_oficina    = future_transacciones_oficina.result()

        future_transacciones_bodega = executor.submit(getradio, grupo=grupo , inputvar = {'precuso':['008','025','033','091','093','097']})
        data_transaciones_bodega    = future_transacciones_bodega.result()

        future_transacciones_apartamento = executor.submit(getradio, grupo=grupo , inputvar = {'precuso':['002','038']})
        data_transaciones_apartamento    = future_transacciones_apartamento.result()

        future_transacciones_casa = executor.submit(getradio, grupo=grupo , inputvar = {'precuso':['001','037']})
        data_transaciones_casa    = future_transacciones_casa.result()

        future_transacciones_hotel = executor.submit(getradio, grupo=grupo , inputvar = {'precuso':['021','026','027','046']})
        data_transaciones_hotel    = future_transacciones_hotel.result()

    formato = [{'tipo':'Transacciones','tipoinmueble':'Local','data':data_transaciones_local,'median':None,'min':None,'max':None},
               {'tipo':'Transacciones','tipoinmueble':'Oficina','data':data_transaciones_oficina,'median':None,'min':None,'max':None},
               {'tipo':'Transacciones','tipoinmueble':'Bodega','data':data_transaciones_bodega,'median':None,'min':None,'max':None},
               {'tipo':'Transacciones','tipoinmueble':'Apartamento','data':data_transaciones_apartamento,'median':None,'min':None,'max':None},
               {'tipo':'Transacciones','tipoinmueble':'Casa','data':data_transaciones_casa,'median':None,'min':None,'max':None},
               {'tipo':'Transacciones','tipoinmueble':'Hotel','data':data_transaciones_hotel,'median':None,'min':None,'max':None}]
    
    for i in formato:
        try: i['median'] = i['data'][0][500]['valortransacciones']['value']
        except: pass
        del  i['data']
        
    return pd.DataFrame(formato)

@st.cache_data(show_spinner=False)
def get_pot_general(data_analisis_pot=pd.DataFrame()):
    
    output = {}
    if not data_analisis_pot.empty:
        max_altura_manzana = max_piso_manzana(data_analisis_lote=data_analisis_pot)
        try: output = {'max_altura_manzana':int(round(max_altura_manzana+0.49,0)) }
        except: pass
    
    if not data_analisis_pot.empty and 'variable' in data_analisis_pot:
        
        # Altura maxima
        max_altura = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='tratamiento_urbanistico-alturamax']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            datapaso['valor'] = pd.to_numeric(datapaso['valor'],errors='coerce')
            datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            max_altura = datapaso['valor'].max()
            # mayor piso construido en la manzana
    
        # Tipo de tratamiento
        tipotratamiento = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='tratamiento_urbanistico-nombretra']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            tipotratamiento = '|'.join(datapaso['valor'].astype(str).unique())
                
        # Tipo de tratamiento       
        tipologia = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='tratamiento_urbanistico-tipologia']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            tipologia = '|'.join(datapaso['valor'].astype(str).unique())
                
        # Area de actividad
        area_actividad = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='area_actividad_-_pot_bogota_d-nombreare']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            area_actividad = '|'.join(datapaso['valor'].astype(str).unique())
                     
        # Actuacion estrategica
        actuacion_estrategica = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='actuacion_estrategica-nombre']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            actuacion_estrategica = '|'.join(datapaso['valor'].astype(str).unique())
        else:
            actuacion_estrategica = 'No aplica'
                        
        # Antejardin
        antejarin_dimension_min = None
        antejarin_dimension_max = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='antejardin-dimension']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            datapaso['valor'] = pd.to_numeric(datapaso['valor'],errors='coerce')
            datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            antejarin_dimension_min = datapaso['valor'].min()    
            antejarin_dimension_max = datapaso['valor'].max()   
    
        # Antejardin observaciones
        antejarin_obs = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='antejardin-observacio']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            antejarin_obs = '|'.join(datapaso['valor'].astype(str).unique())
                
                
        # Bienes de interes cultural - Nombre
        cultual_nombre = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='bien_interes_cultural-bic-nombre']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            cultual_nombre = '|'.join(datapaso['valor'].astype(str).unique())
            
        # Bienes de interes cultural - Categoria
        cultual_categoria = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='bien_interes_cultural-bic-categoria']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            cultual_categoria = '|'.join(datapaso['valor'].astype(str).unique())
                    
        # Area de elevacion maxima - elevacion [AERONAUTICA]
        elevacion_aeronautica = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='area_elevacion_maxima-elevacion']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            elevacion_aeronautica = '|'.join(datapaso['valor'].astype(str).unique())
                    
        # Area de elevacion maxima - altura [AERONAUTICA]
        altura_aeronautica = None
        datapaso = data_analisis_pot[data_analisis_pot['variable']=='area_elevacion_maxima-altura']
        datapaso = datapaso[datapaso['valor'].notnull()]
        if not datapaso.empty:
            altura_aeronautica = '|'.join(datapaso['valor'].astype(str).unique())
                               

        output.update({'max_altura':max_altura,'tipotratamiento':tipotratamiento,'tipologia':tipologia,
               'antejarin_dimension_min':antejarin_dimension_min,'antejarin_dimension_max':antejarin_dimension_max,
               'antejarin_obs':antejarin_obs,'cultual_nombre':cultual_nombre,'cultual_categoria':cultual_categoria,
               'elevacion_aeronautica':elevacion_aeronautica,'altura_aeronautica':altura_aeronautica,
               'area_actividad':area_actividad,'actuacion_estrategica':actuacion_estrategica})
        
    return output
        
@st.cache_data(show_spinner=False)       
def max_piso_manzana(data_analisis_lote=pd.DataFrame()):
    resultado = None

    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]

    values   = data_analisis_lote['barmanpre'].apply(lambda x: x[0:9])
    query    = " OR ".join([f"barmanpre LIKE '{value}%'" for value in list(values.unique())])

    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query(f"SELECT grupo FROM  bigdata.bogota_lotes_point WHERE {query}" , engine)
    engine.dispose()

    listagroup = list(data['grupo'].astype(str).unique())
    data       = datacaracteristicas(grupo=listagroup,variables='grupo,barmanpre,general_catastro')
    if not data.empty:
        variable = 'general_catastro'
        df           = data[data[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
        df           = pd.DataFrame(df)
        df.columns   = ['formato']
        df           = pd.json_normalize(df['formato'])
        if not df.empty and 'connpisos' in df:
            df['connpisos'] = pd.to_numeric(df['connpisos'],errors='coerce')
            resultado       = df['connpisos'].max()
    return resultado

def alturamax(info_pot):
    info_pot['altura_index'] = None
    
    if "max_altura" in info_pot:
        if isinstance(info_pot["max_altura"],(int,float)):
            info_pot['altura_index'] = info_pot["max_altura"]
        elif isinstance(info_pot["max_altura"],str):
            info_pot['altura_index'] = convertir_string_a_numero(info_pot["max_altura"]) if info_pot["max_altura"]!='' else None
    
    if info_pot['altura_index'] is None and "max_altura_manzana" in info_pot:
        if isinstance(info_pot["max_altura_manzana"],(int,float)):
            info_pot['altura_index'] = info_pot["max_altura_manzana"]
            
    return info_pot

def convertir_string_a_numero(s):
    if s.isdigit():
        return int(s)
    if re.search(r'[a-zA-Z]', s):
        return None
    partes = re.split(r'[^0-9]', s)
    numeros = [int(parte) for parte in partes if parte.isdigit()]
    if numeros:
        return max(numeros)
    return None


# reserva vial 
# precios uso del suelo

# precios de referencia nuevos y transacciones

# v = data_analisis_pot[data_analisis_pot['variable'].str.contains('tratamiento_urbanistico')]
