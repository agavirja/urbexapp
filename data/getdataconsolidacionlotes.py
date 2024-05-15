import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
from shapely.ops import cascaded_union,unary_union
from sqlalchemy import create_engine 
from datetime import datetime

from data.inmuebleANDusosuelo import inmueble2usosuelo
from data.getuso_destino import getuso_destino
from data.combinacion_poligonos import combinapolygons,num_combinaciones_lote

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
    
    datapredios       = pd.DataFrame()
    datalotescatastro = pd.DataFrame()  
    
    if isinstance(polygon, str):
        datamanzana = pd.read_sql_query(f"SELECT mancodigo as manzcodigo FROM  pot.data_bogota_manzana WHERE ST_CONTAINS(ST_GEOMFROMTEXT('{polygon}'), geometry)" , engine)
        
        if not datamanzana.empty:
            query       = "','".join(datamanzana['manzcodigo'].unique())
            query       = f" manzcodigo IN ('{query}')"   
            if areamin>0:
                query += f' AND preaterre>={areamin}'
            if areamax>0:
                query += f' AND preaterre<={areamax}'
            if maxpredios>0:
                query += f' AND predios<={maxpredios}'
            if maxpiso>0:
                query += f' AND maxpisos<={maxpiso}'
            if loteesquinero is not None and isinstance(loteesquinero, str) and 'todo' not in loteesquinero.lower():
                if 'si' in loteesquinero.lower():
                    query += ' AND esquinero=1'
                elif 'no' in loteesquinero.lower():
                    query += ' AND esquinero=0'
            datapredios = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_consolidacion_lotes_2000 WHERE {query}" , engine)
            
    if not datapredios.empty:
        #-----------------------------------------------------------------#
        # Merge polygons
        barmanprelist = datapredios['barmanpre'].str.split('|')
        barmanprelist = [codigo for sublist in barmanprelist for codigo in sublist]
        barmanprelist = list(set(barmanprelist))
        
        query = "','".join(barmanprelist)
        query = f" lotcodigo IN ('{query}')"   
        datalotescatastro = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
        datalotescatastro = datalotescatastro.drop_duplicates(subset='barmanpre',keep='first')
        
        datapredios = combinapolygons(datapredios.copy(),datalotescatastro.copy())
        datapredios = datapredios[datapredios['wkt'].notnull()]
        datapredios['geometry'] = gpd.GeoSeries.from_wkt(datapredios['wkt'])
        datapredios             = gpd.GeoDataFrame(datapredios, geometry='geometry')

        #-----------------------------------------------------------------#
        # P.O.T
        #-----------------------------------------------------------------#
        datapredios = mergePOT(datapredios.copy(),polygon,pot,engine)      
        datapredios,datalotescatastro = num_combinaciones_lote(datapredios,datalotescatastro)

    if not datapredios.empty:
        #-----------------------------------------------------------------#
        # Vias
        #-----------------------------------------------------------------#
        if viaprincipal is not None and isinstance(viaprincipal, str) and 'todo' not in viaprincipal.lower():
            barmanprelist = datapredios['barmanpre'].str.split('|')
            barmanprelist = [codigo for sublist in barmanprelist for codigo in sublist]
            barmanprelist = list(set(barmanprelist))
    
            query = "','".join(barmanprelist)
            query = f" barmanpre IN ('{query}')"   
            dataviasprincipales = pd.read_sql_query(f"SELECT  barmanpre,tipo FROM  bigdata.bogota_barmanpre_via_principal WHERE {query}" , engine)
            idd = datapredios['barmanpre'].str.contains( '|'.join(dataviasprincipales['barmanpre'].unique()) )
            if 'si' in viaprincipal.lower():
                datapredios = datapredios[idd]
            elif 'no' in viaprincipal.lower():
                datapredios = datapredios[~idd]
    engine.dispose()
    return datapredios,datalotescatastro

@st.cache_data(show_spinner=False)
def getlotebycod(codigos):
    
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = st.secrets["schema_bigdata"]
    engine      = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    datapredios   = pd.DataFrame()
    datacompacta  = pd.DataFrame()
    datausosuelo  = pd.DataFrame()
    dataactividad = pd.DataFrame()
    
    if isinstance(codigos, str):
        query       = "','".join(codigos.split('|'))
        query       = f" id IN ('{query}')"   
        datapredios = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_consolidacion_lotes_2000 WHERE {query}" , engine)

        if not datapredios.empty:
            barmanprelist = datapredios['barmanpre'].str.split('|')
            barmanprelist = [codigo for sublist in barmanprelist for codigo in sublist]
            barmanprelist = list(set(barmanprelist))

            query = "','".join(barmanprelist)
            query = f" lotcodigo IN ('{query}')"   
            datalotescatastro = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
            datalotescatastro = datalotescatastro.drop_duplicates(subset='barmanpre',keep='first')

            datapredios = combinapolygons(datapredios.copy(),datalotescatastro.copy())
            datapredios['geometry'] = gpd.GeoSeries.from_wkt(datapredios['wkt'])
            datapredios             = gpd.GeoDataFrame(datapredios, geometry='geometry')

            query         = "','".join(barmanprelist)
            query         = f" barmanpre IN ('{query}')"
            datacompacta  = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_catastro_compacta WHERE {query}" , engine)
            datausosuelo  = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)
            dataactividad = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_catastro_compacta_precdestin WHERE {query}" , engine)

            dataprecuso,dataprecdestin = getuso_destino()
            dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
            dataprecdestin.rename(columns={'codigo':'precdestin','tipo':'actividad','descripcion':'desc_actividad'},inplace=True)
            if not datausosuelo.empty:
                datausosuelo  = datausosuelo.merge(dataprecuso,on='precuso',how='left',validate='m:1')
            if not dataactividad.empty:
                dataactividad = dataactividad.merge(dataprecdestin,on='precdestin',how='left',validate='m:1')
                
    engine.dispose()
    return datapredios,datacompacta,datausosuelo,dataactividad

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
