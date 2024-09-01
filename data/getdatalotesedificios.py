import streamlit as st
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def main(inputvar):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    polygon        = inputvar['polygon'] if 'polygon' in inputvar and isinstance(inputvar['polygon'], str) else None
    pot            = inputvar['pot']  if 'pot'  in inputvar else []
    areamin        = inputvar['areamin'] if 'areamin' in inputvar else 0
    areamax        = inputvar['areamax'] if 'areamax' in inputvar else 0
    antiguedadmin  = inputvar['antiguedadmin'] if 'antiguedadmin' in inputvar else 0
    antiguedadmax  = inputvar['antiguedadmax'] if 'antiguedadmax' in inputvar else 0
    loteesquinero  = inputvar['loteesquinero'] if 'loteesquinero' in inputvar else None
    viaprincipal   = inputvar['viaprincipal']  if 'viaprincipal'  in inputvar else None
    frente         = inputvar['frente'] if 'frente' in inputvar else 0
    maxpredios     = inputvar['maxpredios'] if 'maxpredios' in inputvar else 0
    maxpropietario = inputvar['maxpropietario'] if 'maxpropietario' in inputvar else 0
    maxavaluo      = inputvar['maxavaluo'] if 'maxavaluo' in inputvar else 0
    maxpiso        = inputvar['maxpiso'] if 'maxpiso' in inputvar else 0
    usodelsuelo    = inputvar['usodelsuelo'] if 'usodelsuelo' in inputvar else None
    tipoedificio   = inputvar['tipoedificio'] if 'tipoedificio' in inputvar else 'Todos'
    
    
    # Con el uso del suelo filtrar tipo de inmueble 
    tipoinmueble = 'Todos'
    # con el pot filtrar los lotes
    
    data,datalotes = [pd.DataFrame()]*2
    if isinstance(polygon, str):
        query = ''
        if areamin>0:
            query += f' AND areaconstruida_total>={areamin}'
        if areamax>0:
            query += f' AND areaconstruida_total<={areamax}'
        if maxpropietario>0:
            query += f' AND propietarios<={maxpropietario}'
        if maxpredios>0:
            query += f' AND predios<={maxpredios}'
        if maxavaluo>0:
            query += f' AND total_avaluo<={maxavaluo}'
        if not 'todo' in tipoinmueble.lower():
            query += f' AND tipoinmueble="{tipoinmueble}"'
        if isinstance(polygon, str):
            query += f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))'
            
        if query !="":
            query     = query.strip().strip('AND')
            data      = pd.read_sql_query(f"SELECT * FROM  bigdata.data_groupbarmanpre WHERE {query}" , engine)
            datalotes = pd.DataFrame()
            if not data.empty:
                lotlist   = "','".join(data['barmanpre'].unique())
                query     = f" lotcodigo IN ('{lotlist}')"        
                datalotes = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
                datamerge = data.drop_duplicates(subset='barmanpre',keep='first')
                datalotes = datalotes.merge(datamerge,on='barmanpre',how='left',validate='m:1')

    engine.dispose()
    return data,datalotes

#-----------------------------------------------------------------------------#
# P.O.T
#-----------------------------------------------------------------------------#
def mergePOT(datapredios,polygon,pot,engine):
    if pot is not None and pot!=[]:
        for items in pot:
            #-------------------------------------------------------------#
            # Tratamiento urbanistico
            if 'tipo' in items and 'tratamientourbanistico' in items['tipo']:
                consulta = ''
                if 'alturaminpot' in items and items['alturaminpot']>0:
                    consulta += f" AND (alturamax_num>={items['alturaminpot']} OR alturamax_num IS NULL)"
                if 'tratamiento' in items and items['tratamiento']!=[]:
                    query    = "','".join(items['tratamiento'])
                    consulta += f" AND nombretra IN ('{query}')"
                
                if consulta!='':
                    consulta        = consulta.strip().strip('AND')+' AND '
                    datatratamiento = pd.read_sql_query(f"SELECT ST_AsText(geometry) AS geometry FROM  pot.bogota_tratamientourbanistico WHERE {consulta} (ST_CONTAINS(ST_GEOMFROMTEXT('{polygon}'), geometry) OR ST_Intersects(geometry,ST_GEOMFROMTEXT('{polygon}')) OR ST_Touches(geometry,ST_GEOMFROMTEXT('{polygon}')))" , engine)
                    datatratamiento['geometry'] = gpd.GeoSeries.from_wkt(datatratamiento['geometry'])
                    datatratamiento = gpd.GeoDataFrame(datatratamiento, geometry='geometry')
                    datatratamiento['isin'] = 1
                    
                    datapredios = gpd.sjoin(datapredios, datatratamiento, how="left", op="intersects")
                    datapredios = datapredios[datapredios['isin']==1]
                    datapredios = datapredios.drop_duplicates(subset='id',keep='first')
                    variables   = [x for x in ['isin','index_left','index_right'] if x in datapredios]
                    datapredios.drop(columns=variables,inplace=True)
                
            #-------------------------------------------------------------#
            # Area de actividad
            if 'tipo' in items and 'areaactividad' in items['tipo']:
                consulta = ''
                if 'nombreare' in items and items['nombreare']!=[]:
                    query    = "','".join(items['nombreare'])
                    consulta += f"nombreare IN ('{query}')"
                if consulta!='':
                    consulta      = consulta.strip().strip('AND')+' AND '
                    dataactividad = pd.read_sql_query(f"SELECT ST_AsText(geometry) AS geometry FROM  pot.bogota_areaactividad WHERE {consulta} (ST_CONTAINS(ST_GEOMFROMTEXT('{polygon}'), geometry) OR ST_Intersects(geometry,ST_GEOMFROMTEXT('{polygon}')) OR ST_Touches(geometry,ST_GEOMFROMTEXT('{polygon}')))" , engine)
                    dataactividad['geometry'] = gpd.GeoSeries.from_wkt(dataactividad['geometry'])
                    dataactividad = gpd.GeoDataFrame(dataactividad, geometry='geometry')
                    dataactividad['isin'] = 1
                    
                    datapredios = gpd.sjoin(datapredios, dataactividad, how="left", op="intersects")
                    datapredios = datapredios[datapredios['isin']==1]
                    datapredios = datapredios.drop_duplicates(subset='id',keep='first')
                    variables   = [x for x in ['isin','index_left','index_right'] if x in datapredios]
                    datapredios.drop(columns=variables,inplace=True)
            
            #-------------------------------------------------------------#
            # Actuacion Estrategica
            if 'tipo' in items and 'actuacionestrategica' in items['tipo']:
                if 'isin' in items and any([w for w in ['si','no'] if w in items['isin'].lower()]):
                    datactuacionestrategica = pd.read_sql_query(f"SELECT ST_AsText(geometry) AS geometry FROM  pot.bogota_actuacionestrategica WHERE (ST_CONTAINS(ST_GEOMFROMTEXT('{polygon}'), geometry) OR ST_Intersects(geometry,ST_GEOMFROMTEXT('{polygon}')) OR ST_Touches(geometry,ST_GEOMFROMTEXT('{polygon}')))" , engine)
                    datactuacionestrategica['geometry'] = gpd.GeoSeries.from_wkt(datactuacionestrategica['geometry'])
                    datactuacionestrategica = gpd.GeoDataFrame(datactuacionestrategica, geometry='geometry')
                    datactuacionestrategica['isin'] = 1
                    datapredios = gpd.sjoin(datapredios, datactuacionestrategica, how="left", op="intersects")
                    
                    if 'si' in items['isin'].lower():
                        datapredios = datapredios[datapredios['isin']==1]
                    elif 'no' in items['isin'].lower():
                        datapredios = datapredios[datapredios['isin'].isnull()]
                    datapredios = datapredios.drop_duplicates(subset='id',keep='first')
                    variables   = [x for x in ['isin','index_left','index_right'] if x in datapredios]
                    datapredios.drop(columns=variables,inplace=True)
            
    return datapredios
