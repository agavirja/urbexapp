import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine 
from geopy.distance import geodesic

from functions.getuso_destino import usosuelo_class

user     = st.secrets["user_write_urbex"]
password = st.secrets["password_write_urbex"]
host     = st.secrets["host_read_urbex"]
schema   = st.secrets["schema_write_urbex"]
engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

@st.cache_data(show_spinner=False)
def main(data=pd.DataFrame(), datageometry=pd.DataFrame(), inputvar={}):

    #-------------------------------------------------------------------------#
    #Filtros: 
    areamin          = inputvar['areamin'] if 'areamin' in inputvar and isinstance(inputvar['areamin'], (int, float)) else 0 
    areamax          = inputvar['areamax'] if 'areamax' in inputvar and isinstance(inputvar['areamax'], (int, float)) else 0 
    desde_antiguedad = inputvar['desde_antiguedad'] if 'desde_antiguedad' in inputvar and isinstance(inputvar['desde_antiguedad'], (int, float)) else 0 
    hasta_antiguedad = inputvar['hasta_antiguedad'] if 'hasta_antiguedad' in inputvar and isinstance(inputvar['hasta_antiguedad'], (int, float)) else 0 
    pisosmin         = inputvar['pisosmin'] if 'pisosmin' in inputvar and isinstance(inputvar['pisosmin'], (int, float)) else 0 
    pisosmax         = inputvar['pisosmax'] if 'pisosmax' in inputvar and isinstance(inputvar['pisosmax'], (int, float)) else 0 
    estratomin       = inputvar['estratomin'] if 'estratomin' in inputvar and isinstance(inputvar['estratomin'], (int, float)) else 0 
    estratomax       = inputvar['estratomax'] if 'estratomax' in inputvar and isinstance(inputvar['estratomax'], (int, float)) else 0 
    precuso          = inputvar['precuso'] if 'precuso' in inputvar and isinstance(inputvar['precuso'], list) else [] 

        # Inputs para calcular la ditancia frente a un punto de referencia
    latitud_ref  = inputvar['latitud'] if 'latitud' in inputvar and isinstance(inputvar['latitud'], (int, float)) else None 
    longitud_ref = inputvar['longitud'] if 'longitud' in inputvar and isinstance(inputvar['longitud'], (int, float)) else None 
    metros       = inputvar['metros'] if 'metros' in inputvar and isinstance(inputvar['metros'], (int, float)) else None 

    if not data.empty and 'grupo' in data:
        
        #---------------------------------------------------------------------#
        # Filtro por Distancia
        if not datageometry.empty and 'latitud' in datageometry and 'longitud' in datageometry and 'distancia' not in data:
            datageometry = datageometry[(datageometry['latitud'].notnull()) & (datageometry['longitud'].notnull())]
            if not datageometry.empty and 'distancia' not in datageometry: 
                lat_rad     = np.radians(datageometry['latitud'])
                lon_rad     = np.radians(datageometry['longitud'])
                ref_lat_rad = np.radians(latitud_ref)
                ref_lon_rad = np.radians(longitud_ref)
    
                # Haversine formula
                dlat = lat_rad - ref_lat_rad
                dlon = lon_rad - ref_lon_rad
                a    = np.sin(dlat/2)**2 + np.cos(lat_rad) * np.cos(ref_lat_rad) * np.sin(dlon/2)**2
                c    = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
                R    = 6371000
                datageometry['distancia'] = R * c

        if not datageometry.empty and 'distancia' in datageometry and 'distancia' not in data: 
            datamerge = datageometry.drop_duplicates(subset='grupo',keep='first')
            data      = data.merge(datamerge[['grupo','distancia']],on='grupo',how='left',validate='m:1')
        
        if not data.empty: 
            #---------------------------------------------------------------------#
            # Filtro por area 
            if areamin>0 and 'preaconst' in data:
                data = data[data['preaconst']>=areamin]
            if areamax>0 and 'preaconst' in data:
                data = data[data['preaconst']<=areamax]
            #---------------------------------------------------------------------#
            # Filtro por antiguedad:
            if desde_antiguedad>0 and 'prevetustzmin' in data:
                data = data[data['prevetustzmin']>=desde_antiguedad]
            if hasta_antiguedad>0 and 'prevetustzmax' in data:
                data = data[data['prevetustzmax']<=hasta_antiguedad]
            #---------------------------------------------------------------------#
            # Filtro por antiguedad:
            if pisosmin>0 and 'connpisos' in data:
                data = data[data['connpisos']>=pisosmin]
            if pisosmax>0 and 'connpisos' in data:
                data = data[data['connpisos']<=pisosmax]
            #---------------------------------------------------------------------#
            # Filtro por estrato:
            if estratomin>0 and 'estrato' in data:
                data = data[data['estrato']>=estratomin]
            if estratomax>0 and 'estrato' in data:
                data = data[data['estrato']<=estratomax]
            #---------------------------------------------------------------------#
            # Filtro por distancia:
            if metros is not None and metros>0 and 'distancia' in data:
                data = data[data['distancia']<=metros]
            #---------------------------------------------------------------------#
            # Filtro por precuso:
            if isinstance(precuso,list) and precuso!=[] and 'precuso' in data:
                data = data[(data['precuso'].isin(precuso)) | (data['precuso'].isnull())]
            
    return data

def calcular_distancia(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).meters