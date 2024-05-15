import streamlit as st
import pandas as pd
import mysql.connector as sql
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def main(latitud,longitud):
    
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = 'pot'
    result      = []
    
    formato = [
        {'tabla':'bogota_tratamientourbanistico','nombre':'Tratamiento Urbanistico','variables':[{'variable':'nombretra','nombre':'Tipo de tratamiento'},{'variable':'tipologia','nombre':'Tipología'},{'variable':'alturamax','nombre':'Altura máx'},{'variable':'numeroact','nombre':'Acto admin'}]},
        {'tabla':'bogota_areaactividad','nombre':'Área de actividad','variables':[{'variable':'nombreare','nombre':'Nombre'}]},
        {'tabla':'bogota_actuacionestrategica','nombre':'Actuación Estratégica','variables':[{'variable':'nombre','nombre':'Nombre'},{'variable':'priorizaci','nombre':'Priorización'}]},
        {'tabla':'bogota_unidadplaneamientolocal','nombre':'UPL','variables':[{'variable':'codigoupl','nombre':'Código'},{'variable':'nombre','nombre':'Nombre'}]},
        {'tabla':'bogota_amenazaindesbordamiento','nombre':'Amenaza desbordamiento','variables':[{'variable':'categoriza','nombre':'Categoría'},{'variable':'escenrio','nombre':'Escenario'},{'variable':'clasesuel','nombre':'Clase suelo'},{'variable':'areazonif','nombre':'Área'}]},
        {'tabla':'bogota_amenazammrural','nombre':'Movimiento en masa','variables':[{'variable':'clasesuel','nombre':'Clase'},{'variable':'areazonif','nombre':'Área'}]},
        {'tabla':'bogota_planparcial','nombre':'Plan parcial','variables':[{'variable':'nombre','nombre':'Nombre'}]},
        {'tabla':'bogota_zonaindustrial','nombre':'Zona industrial','variables':[{'variable':'ambitoint','nombre':'Ambito'}] },
        ]
    
    if latitud is not None and longitud is not None: 
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        for items in formato:
            try:
                datapaso  = pd.DataFrame()
                table     = items['tabla']
                variables = items['variables']
                varlist   = ''
                for j in variables:
                    if 'variable' in j:
                        varlist += f",{j['variable']}"
                if varlist!='':
                    varlist  = varlist.strip(',')
                    datapaso = pd.read_sql_query(f"SELECT {varlist} FROM {schema}.{table} WHERE ST_CONTAINS(geometry, POINT({longitud},{latitud}))" , engine)
                if not datapaso.empty:
                    r = {}
                    for j in variables:
                        if 'variable' in j and 'nombre' in j:
                            r.update({j['variable']:j['nombre']})
                    datapaso.rename(columns=r,inplace=True)
                    result.append({'nombre':items['nombre'],'data':datapaso.iloc[0].to_dict()})
                else:
                    result.append({'nombre':items['nombre'],'data':{'':'No aplica'}})

            except: pass
        engine.dispose()
    return result