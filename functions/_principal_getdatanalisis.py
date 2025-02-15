import streamlit as st
import pandas as pd
import numpy as np
import concurrent.futures
import geopandas as gpd
import shapely.wkt as wkt

from functions.getuso_destino import getuso_destino,usosuelo_class
from functions.getuso_tipoinmueble import usosuelo2inmueble
from functions._principal_getdatalotes import main as getdatalotes
from functions.polygonunion import polygonunion

from data._principal_transacciones import data_transacciones,estadisticas_transacciones
from data._principal_prediales import data_prediales,estadisticas_prediales
from data._principal_lotes import datalote
from data._principal_lotes_radio import data_lotes_radio
from data.filters import main as filters
from data._principal_caracteristicas import datapredios,estadisticas_predios

@st.cache_data(show_spinner=False)
def main(grupo=None,polygon=None,inputvar={}):

    #-------------------------------------------------------------------------#
    # get data
    data_analisis_lote, data_geometry, data_analisis_transacciones, data_analisis_prediales, data_analisis_prediostotal, latitud_ref, longitud_ref, polygon, tipoconsulta = getalldata(grupo=grupo, polygon=polygon)
    
    #-------------------------------------------------------------------------#
    # Filtros
    data_analisis_transacciones = filters(data=data_analisis_transacciones, datageometry=pd.DataFrame(), inputvar=inputvar)
    data_analisis_prediales     = filters(data=data_analisis_prediales,     datageometry=pd.DataFrame(), inputvar=inputvar)
    data_analisis_prediostotal  = filters(data=data_analisis_prediostotal,  datageometry=pd.DataFrame(), inputvar=inputvar)

    data_geometry  = data_geometry[data_geometry['grupo'].isin(data_analisis_prediostotal['grupo'])] if not data_geometry.empty else data_geometry
    
    #-------------------------------------------------------------------------#
    # Estadisticas
    if 'radio' in tipoconsulta: 
        output = multiple_radio(data_analisis_lote=data_analisis_lote, data_analisis_transacciones=data_analisis_transacciones, data_analisis_prediales=data_analisis_prediales, data_analisis_prediostotal=data_analisis_prediostotal, latref=latitud_ref,lngref=longitud_ref)
    elif 'polygon' in tipoconsulta:
        if 'metros' in inputvar: del inputvar['metros']
        output = filtros(data_analisis_lote=data_analisis_lote, data_geometry=data_geometry, data_analisis_transacciones=data_analisis_transacciones, data_analisis_prediales=data_analisis_prediales, data_analisis_prediostotal=data_analisis_prediostotal, inputvar={}, latref=None, lngref=None)
        
    return  output,data_analisis_lote,data_geometry, latitud_ref, longitud_ref, polygon


@st.cache_data(show_spinner=False)
def getalldata(grupo=None,polygon=None): 
    
    listagrupos                 = []
    data_geometry               = pd.DataFrame(columns=['grupo', 'barmanpre', 'latitud', 'longitud', 'wkt'])
    data_analisis_lote          = pd.DataFrame(columns=['grupo', 'barmanpre', 'latitud', 'longitud', 'wkt'])
    data_analisis_prediales     = pd.DataFrame()
    data_analisis_transacciones = pd.DataFrame()
    data_analisis_prediostotal  = pd.DataFrame()
    tipoconsulta                = 'radio' # defecto 
    
    #-------------------------------------------------------------------------#
    # Grupo: trae el radio para un lote en particular o lista de lotes
    if grupo is not None:
        data_geometry = data_lotes_radio(grupo=grupo)
        listagrupos   = list(data_geometry['grupo'].astype(str).unique())
        
    #-------------------------------------------------------------------------#
    # Polygon: Cuando la consulta es sobre un poligono particular
    elif polygon is not None and isinstance(polygon, str) and polygon!='' and not 'none' in polygon.lower():
        data_getlotes = getdatalotes(inputvar={'polygon':polygon})
        tipoconsulta  = 'polygon'
        
        if not data_getlotes.empty:
            listagrupos   = list(data_getlotes['grupo'].astype(str).unique())
            
            data_geometry             = data_getlotes[['grupo', 'barmanpre',  'wkt']]
            data_geometry['geometry'] = gpd.GeoSeries.from_wkt(data_geometry['wkt'])
            data_geometry             = gpd.GeoDataFrame(data_geometry, geometry='geometry')
            data_geometry['latitud']  = data_geometry['geometry'].apply(lambda x: x.centroid.y)
            data_geometry['longitud'] = data_geometry['geometry'].apply(lambda x: x.centroid.x)
            data_geometry.drop(columns=['geometry'],inplace=True)
            data_geometry = pd.DataFrame(data_geometry)
            
    #-------------------------------------------------------------------------#
    # Cargar la data
    if isinstance(listagrupos,list) and listagrupos!=[]:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_transacciones = executor.submit(data_transacciones, grupo=listagrupos)
            future_datalote      = executor.submit(datalote          , grupo=listagrupos)
            future_prediales     = executor.submit(data_prediales    , grupo=listagrupos, seleccion=0)
            future_prediostotal  = executor.submit(datapredios       , grupo=listagrupos)
            
            data_analisis_transacciones = future_transacciones.result()
            data_analisis_lote          = future_datalote.result()
            data_analisis_prediales     = future_prediales.result()
            data_analisis_prediostotal  = future_prediostotal.result()
    
    #-------------------------------------------------------------------------#
    # Lat/lng referencia 
    latitud_ref  = None
    longitud_ref = None
    
    if isinstance(grupo,str) and grupo!='':
        grupo = grupo.split('|')
    elif isinstance(grupo,(float,int)):
        grupo = [f'{grupo}']
    if isinstance(grupo,list) and grupo!=[]:
        grupo        = list(map(str, grupo))
        latitud_ref  = data_geometry[data_geometry['grupo'].astype(str).isin(grupo)]['latitud'].median() if not data_geometry.empty  and 'grupo' in data_geometry and 'latitud'  in data_geometry  else None
        longitud_ref = data_geometry[data_geometry['grupo'].astype(str).isin(grupo)]['longitud'].median() if not data_geometry.empty and 'grupo' in data_geometry and 'longitud' in data_geometry else None
        
        datapaso = data_geometry[(data_geometry['grupo'].astype(str).isin(grupo)) | (data_geometry['grupo'].isin(grupo))] if not data_geometry.empty else pd.DataFrame(columns=['grupo', 'barmanpre', 'latitud', 'longitud', 'wkt', 'distancia'])
        polygon  = datapaso['wkt'].iloc[0] if not datapaso.empty and 'wkt' in datapaso else None
        if not datapaso.empty:
            try:
                df      = polygonunion(datapaso)
                polygon = df['wkt'].iloc[0]
            except: pass

    if latitud_ref is None and longitud_ref is None and 'polygon' in tipoconsulta:
        P            = wkt.loads(polygon)
        latitud_ref  = P.centroid.y
        longitud_ref = P.centroid.x
        
    if latitud_ref is None and longitud_ref:
        latitud_ref  = data_analisis_lote['latitud'].median()  if (pd.isna(latitud_ref)  or latitud_ref is None) and not data_analisis_lote.empty and 'latitud' in data_analisis_lote else latitud_ref
        longitud_ref = data_analisis_lote['longitud'].median() if (pd.isna(longitud_ref) or longitud_ref is None) and not data_analisis_lote.empty and 'longitud' in data_analisis_lote else longitud_ref
    
    #-------------------------------------------------------------------------#
    # Merge data general
    data_analisis_transacciones = merge_latlng(data_geometry=data_geometry, data=data_analisis_transacciones, datatotalpredios=data_analisis_prediostotal, latref=latitud_ref, lngref=longitud_ref)
    data_analisis_prediales     = merge_latlng(data_geometry=data_geometry, data=data_analisis_prediales, datatotalpredios=data_analisis_prediostotal, latref=latitud_ref, lngref=longitud_ref)
    data_analisis_prediostotal  = merge_latlng(data_geometry=data_geometry, data=data_analisis_prediostotal, datatotalpredios=pd.DataFrame(), latref=latitud_ref, lngref=longitud_ref)
    data_geometry               = merge_latlng(data_geometry=pd.DataFrame(), data=data_geometry, datatotalpredios=data_analisis_prediostotal , latref=latitud_ref, lngref=longitud_ref)
    
    return data_analisis_lote, data_geometry, data_analisis_transacciones, data_analisis_prediales, data_analisis_prediostotal, latitud_ref, longitud_ref, polygon, tipoconsulta


@st.cache_data(show_spinner=False)
def multiple_radio(data_analisis_lote=pd.DataFrame(),data_analisis_transacciones=pd.DataFrame(),data_analisis_prediales=pd.DataFrame(), data_analisis_prediostotal=pd.DataFrame(),latref=None,lngref=None):
    output = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_metros_100 = executor.submit(filtros, data_analisis_lote=data_analisis_lote, data_analisis_transacciones=data_analisis_transacciones, data_analisis_prediales=data_analisis_prediales, data_analisis_prediostotal=data_analisis_prediostotal, inputvar = {'metros':100}, latref=latref, lngref=lngref)
        future_metros_200 = executor.submit(filtros, data_analisis_lote=data_analisis_lote, data_analisis_transacciones=data_analisis_transacciones, data_analisis_prediales=data_analisis_prediales, data_analisis_prediostotal=data_analisis_prediostotal, inputvar = {'metros':200}, latref=latref, lngref=lngref )
        future_metros_300 = executor.submit(filtros, data_analisis_lote=data_analisis_lote, data_analisis_transacciones=data_analisis_transacciones, data_analisis_prediales=data_analisis_prediales, data_analisis_prediostotal=data_analisis_prediostotal, inputvar = {'metros':300}, latref=latref, lngref=lngref )
        future_metros_400 = executor.submit(filtros, data_analisis_lote=data_analisis_lote, data_analisis_transacciones=data_analisis_transacciones, data_analisis_prediales=data_analisis_prediales, data_analisis_prediostotal=data_analisis_prediostotal, inputvar = {'metros':400}, latref=latref, lngref=lngref )
        future_metros_500 = executor.submit(filtros, data_analisis_lote=data_analisis_lote, data_analisis_transacciones=data_analisis_transacciones, data_analisis_prediales=data_analisis_prediales, data_analisis_prediostotal=data_analisis_prediostotal, inputvar = {'metros':500}, latref=latref, lngref=lngref )

        output.update({100:future_metros_100.result()})
        output.update({200:future_metros_200.result()})
        output.update({300:future_metros_300.result()})
        output.update({400:future_metros_400.result()})
        output.update({500:future_metros_500.result()})
    return output

@st.cache_data(show_spinner=False)
def filtros(data_analisis_lote=pd.DataFrame(), data_geometry=pd.DataFrame(), data_analisis_transacciones=pd.DataFrame(), data_analisis_prediales=pd.DataFrame(), data_analisis_prediostotal=pd.DataFrame(), inputvar={}, latref=None, lngref=None):

    if isinstance(inputvar,dict) and inputvar!={} and latref is not None and lngref is not None:
        if 'latitud' not in inputvar:  inputvar['latitud']  = latref
        if 'longitud' not in inputvar: inputvar['longitud'] = lngref

    output = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_transacciones = executor.submit(estadisticas_transacciones, data=data_analisis_transacciones, data_geometry=data_geometry, inputvar=inputvar)
        future_prediales     = executor.submit(estadisticas_prediales, data=data_analisis_prediales, data_geometry=data_geometry, inputvar=inputvar)
        future_prediostotal  = executor.submit(estadisticas_predios, data=data_analisis_prediostotal, data_geometry=data_geometry, inputvar=inputvar)

        output.update(future_transacciones.result())
        output.update(future_prediales.result())
        output.update(future_prediostotal.result())
        
    return output

@st.cache_data(show_spinner=False)
def merge_latlng(data_geometry=pd.DataFrame(),data=pd.DataFrame(),datatotalpredios=pd.DataFrame(), latref=None,lngref=None):
    if not data.empty:
        #---------------------------------------------------------------------#
        # Merge lat / lng 
        if 'latitud' not in data and 'longitud' not in data and not data_geometry.empty:
            datamerge = data_geometry.drop_duplicates(subset='grupo',keep='first')
            datamerge = datamerge[['grupo','latitud','longitud']]
            data      = data.merge(datamerge,on='grupo',how='left',validate='m:1')
            
        #---------------------------------------------------------------------#
        # Merge lat / lng 
        if any([x for x in ['chip','prechip'] if x in data]) and not datatotalpredios.empty:
            variables        = ['preaconst','prevetustzmin','prevetustzmax','connpisos','estrato','precuso']
            variables        = [x for x in variables if x not in data and x in datatotalpredios]
            variables.append('prechip')
            datamerge        = datatotalpredios[variables].drop_duplicates(subset='prechip',keep='first')
            
            if 'chip' in data:
                datamerge.rename(columns={'prechip':'chip'},inplace=True)
                data = data.merge(datamerge,on='chip',how='left',validate='m:1')
            elif 'prechip' in data:
                data = data.merge(datamerge,on='prechip',how='left',validate='m:1')
            
        #---------------------------------------------------------------------#
        # Distancia
        data['distancia'] = None
        if 'latitud' in data and 'longitud' in data:
            if isinstance(latref,(float,int)) and isinstance(lngref,(float,int)):
                idd         = (data['latitud'].notnull()) &  (data['longitud'].notnull())
                lat_rad     = np.radians(data[idd]['latitud'])
                lon_rad     = np.radians(data[idd]['longitud'])
                ref_lat_rad = np.radians(latref)
                ref_lon_rad = np.radians(lngref)
    
                # Haversine formula
                dlat = lat_rad - ref_lat_rad
                dlon = lon_rad - ref_lon_rad
                a    = np.sin(dlat/2)**2 + np.cos(lat_rad) * np.cos(ref_lat_rad) * np.sin(dlon/2)**2
                c    = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
                R    = 6371000
                data.loc[idd,'distancia'] = R * c
    return data
