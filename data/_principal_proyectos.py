import streamlit as st
import pandas as pd
import json
import re
from sqlalchemy import create_engine 

from functions.read_data import execute_query,execute_listing_code_query

@st.cache_data(show_spinner=False)
def datacodeproyectos(grupo=None, variables='*'):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame()
    if isinstance(grupo, (int, float)) and not isinstance(grupo, bool):
        grupo = int(grupo) if isinstance(grupo, float) and grupo.is_integer() else grupo
    if isinstance(grupo,str) and grupo!='':
        grupo = grupo.split('|')
    elif isinstance(grupo,(float,int)):
        grupo = [f'{grupo}']
    if isinstance(grupo,list) and grupo!=[]:
        grupo = list(map(str, grupo))
        if len(grupo)>500:
            data = execute_query(grupo, 'bogota_barmanpre_proyectos', variables=variables, chunk_size=500)
        else:
            lista  = ",".join(grupo)
            query  = f" grupo IN ({lista})"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data   = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_barmanpre_proyectos WHERE {query}", engine)
            engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def dataproyectos(code=None):
    variables = '`codproyecto`,`output`'
    user      = st.secrets["user_write_urbex"]
    password  = st.secrets["password_write_urbex"]
    host      = st.secrets["host_read_urbex"]
    schema    = st.secrets["schema_write_urbex"]
    data      = pd.DataFrame()
    resultado = pd.DataFrame(columns=['activo', 'tipoinmueble', 'tiponegocio', 'areaconstruida', 'habitaciones', 'banos', 'garajes', 'valor', 'fecha_inicial', 'inmobiliaria', 'url_img', 'latitud', 'longitud', 'code'])
    if isinstance(code,str) and code!='':
        code = code.split('|')
    elif isinstance(code,(float,int)):
        code = [f'{code}']
    if isinstance(code,list) and code!=[]:
        code = list(map(str, code))
        if len(code)>500:
            data = execute_listing_code_query(code, 'bogota_bycodigo_proyectos', variables=variables, chunk_size=500)
        else:
            lista  = "','".join(code)
            query  = f" `codproyecto` IN ('{lista}')"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data   = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_bycodigo_proyectos WHERE {query}", engine)
            engine.dispose()
            
    if not data.empty:
        variable     = 'output'
        df           = data[data[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'codproyecto': x['codproyecto']}, axis=1)
        df           = pd.DataFrame(df,columns=['formato'])
        df           = pd.json_normalize(df['formato'])
        resultado    = df.copy()
    return resultado


@st.cache_data(show_spinner=False)
def datacompletaproyectos(grupo=None):
    #grupo            =  610954 # Pueden ser la lista de codigos de lotes 610954|610954|610954 
    
    variables        = 'grupo,barmanpre,radio'
    datacodigos      = datacodeproyectos(grupo=grupo, variables=variables)
    dataradiocodigos = pd.DataFrame()
    
    data_proyectos = pd.DataFrame(columns=['codproyecto', 'codvende', 'vende', 'codconstructor', 'construye', 'direccion', 'estrato', 'fecha_inicio', 'estado', 'financiera', 'activo', 'unidades_proyecto', 'total_proyecto', 'fecha_entrega', 'fecha_desistido', 'fiduciaria', 'tipo', 'tipo_vivienda', 'url', 'vende_smlv', 'zona', 'coc_integral', 'extractor', 'inst_lavad_secadora', 'estufa_gas_elec', 'horno_gas_elec', 'cal_gas_elec', 'chimeneas', 'tinas', 'pta_duchas', 'deposito', 'porteria', 'salon_social', 'parque_inf', 'canchas', 'gimnasio', 'planta_elect', 'ofrece_piscina', 'shut_basuras', 'zonas_humedas', 'no_ascensores_x_torre_minimo', 'observaciones_ascensores', 'bbq', 'zona_mascotas', 'otro', 'parqueaderos', 'tipo_urbanizacion', 'tipo_est', 'fachada', 'vent', 'carpinteria_puertasclosets', 'mueble_cocina', 'meson_cocina', 'meson_banos', 'piso_halles_com', 'piso_halles_viv', 'piso_alcoba', 'piso_zona_social', 'piso_bano', 'piso_cocina', 'muros_coc', 'muros_banos', 'mueble_lavamanos', 'lavad', 'aire_acond', 'prima_altura', 'descripcion_combo_acabados', 'descripcion_del_proyecto', 'muros_interiores', 'tipo_de_sanitario_alcoba_princ', 'pared_ducha', 'tipo_griferia_lav', 'tipo_griferia_ducha', 'tipo_de_sanitario_otros_banos', 'tipo_de_lavamanos', 'tipo_ducha', 'tipo_griferia_lavaplatos', 'sub_zona', 'tipo_vis', 'latitud', 'longitud'])
    data_inmuebles = pd.DataFrame(columns=['codproyecto', 'codinmueble', 'proyecto', 'vende', 'tipo', 'areaconstruida', 'habitaciones', 'banos', 'garajes', 'deposito', 'tipo_garaje', 'tipo_vis', 'estado'])
    data_precios   = pd.DataFrame(columns=['ano', 'precio', 'nuevos', 'desistidos', 'codinmueble', 'codproyecto'])
    
    if not datacodigos.empty:
        variable     = 'radio'
        df           = datacodigos[datacodigos[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
        df           = pd.DataFrame(df,columns=['formato'])
        df           = pd.json_normalize(df['formato'])
        dataradiocodigos = df.copy()

    listacodproyecto = []
    if not dataradiocodigos.empty:
        dataradiocodigos = dataradiocodigos.drop_duplicates(subset='codproyecto',keep='first')
        listacodproyecto = list(dataradiocodigos['codproyecto'].astype(str).unique())
        
    if isinstance(listacodproyecto,list) and listacodproyecto!=[]: 
        data_proyectos  = dataproyectos(code = listacodproyecto)
        if not data_proyectos.empty:
            data_proyectos  = data_proyectos.drop_duplicates(subset='codproyecto',keep='first')
        
    if not data_proyectos.empty:
        variable     = 'proyecto'
        df           = data_proyectos[data_proyectos[variable].notnull()]
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'codproyecto': x['codproyecto']}, axis=1)
        df           = pd.DataFrame(df,columns=['formato'])
        df           = pd.json_normalize(df['formato'])
        data_inmuebles = df.copy()
    
    if not data_inmuebles.empty:
        variable     = 'serie'
        df           = data_inmuebles[data_inmuebles[variable].notnull()]
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'codinmueble':x['codinmueble'],'codproyecto': x['codproyecto']}, axis=1)
        df           = pd.DataFrame(df,columns=['formato'])
        df           = pd.json_normalize(df['formato'])
        data_precios = df.copy()
        
    #-------------------------------------------------------------------------#
    # data proyectos
    if not data_proyectos.empty: 
        variables = [x for x in ['proyecto','id'] if x in data_proyectos]
        if variables!=[]:
            data_proyectos.drop(columns=variables,inplace=True)
            
        for i in ['estado','tipo','tipo_vivienda']:
            if i in data_proyectos: 
                data_proyectos[i] = data_proyectos[i].apply(lambda x: formatovariables(x))
        data_proyectos['estado'] = data_proyectos['estado'].apply(lambda x: x.split(',')[-1])

    #-------------------------------------------------------------------------#
    # data inmuebles
    if not data_inmuebles.empty: 
        variables = [x for x in ['serie','id'] if x in data_inmuebles]
        if variables!=[]:
            data_inmuebles.drop(columns=variables,inplace=True)
        if 'estado' in data_inmuebles: 
            data_inmuebles['estado'] = data_inmuebles['estado'].apply(lambda x: formatovariables(x))
            data_inmuebles['estado'] = data_inmuebles['estado'].apply(lambda x: x.split(',')[-1])

    #-------------------------------------------------------------------------#
    # data pricing
    if not data_precios.empty:
        #---------------------------------------------------------------------#
        # Merge con data inmuebles
        data_precios = data_precios.merge(data_inmuebles,on=['codinmueble','codproyecto'],how='left',validate='m:1')
        if 'valormt2' not in data_precios and 'precio' in data_precios and 'areaconstruida' in data_precios:
            data_precios['valormt2'] = None
            idd = (data_precios['precio']>0) & (data_precios['areaconstruida']>0)
            data_precios.loc[idd,'valormt2'] = data_precios.loc[idd,'precio']/data_precios.loc[idd,'areaconstruida']

        variables = [x for x in list(data_precios) if x in data_proyectos]
        if 'codproyecto' in variables:
            variables.remove('codproyecto')
            
        #---------------------------------------------------------------------#
        # Merge con data data proyectos
        if isinstance(variables,list) and variables!=[]:
            datamerge = data_proyectos.copy()
            datamerge.drop(columns=variables,inplace=True)
            datamerge = datamerge.drop_duplicates(subset='codproyecto',keep='last')
            data_precios = data_precios.merge(datamerge,on='codproyecto',how='left',validate='m:1')
            
        for i in ['fecha_desistido', 'fecha_entrega', 'fecha_inicio']:
            if i in data_precios: 
                data_precios[i] = pd.to_datetime(data_precios[i], unit='ms')
                
    return data_precios

def formatovariables(x):
    try:
        return ','.join([re.sub('[^a-zA-Z]','',w) for w in x.strip('/').split('/')])
    except: 
        return x
