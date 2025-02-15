import streamlit as st
import pandas as pd
import json
import concurrent.futures

from functions.getuso_destino import getuso_destino,usosuelo_class
from functions.getuso_tipoinmueble import usosuelo2inmueble

from data._principal_caracteristicas import datacaracteristicas
from data._principal_lotes import datalote

@st.cache_data(show_spinner=False)
def main(grupo=None):
    #grupo = "180482|180483|180485|180486|186795|186796|186798|186799|350601|729333|708554|708555|754598|756004|810987|810988|804263|804264|817094"
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_caracteristicas = executor.submit(datacaracteristicas, grupo=grupo)
        future_datalote        = executor.submit(datalote, grupo=grupo)

        data_general = future_caracteristicas.result()
        data_lote    = future_datalote.result()

    data_general  = data_general.merge(data_lote,on=['grupo','barmanpre'],how='outer')
    dataresultado = buildata(data_general)
    
    if not dataresultado.empty and not data_general.empty:
        datamerge     = data_general.drop_duplicates(subset=['grupo','barmanpre'],keep='first')
        dataresultado = dataresultado.merge(datamerge[['grupo', 'barmanpre', 'latitud', 'longitud', 'wkt']],on=['grupo','barmanpre'],how='outer')
    
    return dataresultado
    
@st.cache_data(show_spinner=False)
def buildata(datageneral):
    #-------------------------------------------------------------------------#
    # Seccion: Caracteristicas
    dataresultado = pd.DataFrame(columns=['grupo','barmanpre','prenbarrio', 'preaconst', 'preaterre', 'predios', 'connpisos', 'connsotano', 'prevetustzmin', 'prevetustzmax', 'estrato', 'areapolygon', 'esquinero', 'tipovia', 'propietarios', 'avaluo_catastral', 'impuesto_predial'])
    if not datageneral.empty:
        data          = datageneral.copy()
        dataresultado = data[['grupo','barmanpre']]
        formato       = [
            {'column':'general_catastro','variables':['prenbarrio','preaconst','preaterre','predios','connpisos','connsotano','prevetustzmin','prevetustzmax','estrato']},
            {'column':'info_terreno','variables':['areapolygon','esquinero','tipovia']},
            {'column':'infopredial','variables':['propietarios','avaluo_catastral','impuesto_predial']},
            ]
        
        for i in formato:
            item       = i['column']
            variables  = i['variables']
            if item in data:
                df         = data[['barmanpre','grupo',item]]
                df         = df[df[item].notnull()]
                df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
                df         = df[df[item].notnull()]
                df         = df.explode(item)
                df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre'], 'grupo': x['grupo']}, axis=1)
                df         = pd.DataFrame(df)
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
                if isinstance(variables,list) and variables!=[]:
                    variables += ['barmanpre','grupo']
                    variables = [x for x in variables if x in df]
                    df        = df[variables]
                dataresultado  = dataresultado.merge(df,on=['barmanpre','grupo'],how='outer')
    return dataresultado
