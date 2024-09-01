import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def valor_referencia_avaluo(latitud=None,longitud=None,polygon=None):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    data_ref_avaluo_terreno = pd.DataFrame(columns=['mancodigo','vref'])
    data_ref_avaluo_manzana = pd.DataFrame(columns=['mancodigo','grupopter','avaluocom','avaluocat'])
    data_antejardin         = pd.DataFrame(columns=['codigoid', 'dimension', 'nota', 'observacio'])
    
    if isinstance(polygon,str) and polygon!='':    
        data_ref_avaluo_terreno = pd.read_sql_query(f"SELECT mancodigo,vref FROM  bigdata.data_bogota_ref_terreno WHERE ST_CONTAINS(ST_GeomFromText('{polygon}'), geometry) OR ST_TOUCHES(ST_GeomFromText('{polygon}'), geometry) OR ST_INTERSECTS(ST_GeomFromText('{polygon}'), geometry) OR ST_WITHIN(ST_GeomFromText('{polygon}'), geometry)" , engine)
        data_ref_avaluo_manzana = pd.read_sql_query(f"SELECT manzanaid as mancodigo,grupopter,avaluocom,avaluocat FROM  bigdata.data_bogota_ref_avaluo_manzana WHERE ST_CONTAINS(ST_GeomFromText('{polygon}'), geometry) OR ST_TOUCHES(ST_GeomFromText('{polygon}'), geometry) OR ST_INTERSECTS(ST_GeomFromText('{polygon}'), geometry) OR ST_WITHIN(ST_GeomFromText('{polygon}'), geometry)" , engine)
        data_antejardin         = pd.read_sql_query(f"SELECT codigoid,dimension,nota,observacio FROM  pot.bogota_antejardin WHERE ST_CONTAINS(ST_GeomFromText('{polygon}'), geometry) OR ST_TOUCHES(ST_GeomFromText('{polygon}'), geometry) OR ST_INTERSECTS(ST_GeomFromText('{polygon}'), geometry) OR ST_WITHIN(ST_GeomFromText('{polygon}'), geometry)" , engine)
      
    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)) and data_ref_avaluo_terreno.empty and data_ref_avaluo_manzana.empty:
        data_ref_avaluo_terreno = pd.read_sql_query(f"SELECT mancodigo,vref FROM  bigdata.data_bogota_ref_terreno WHERE ST_CONTAINS(geometry,Point({longitud},{latitud}))" , engine)
        data_ref_avaluo_manzana = pd.read_sql_query(f"SELECT manzanaid as mancodigo,grupopter,avaluocom,avaluocat FROM  bigdata.data_bogota_ref_avaluo_manzana WHERE ST_CONTAINS(geometry,Point({longitud},{latitud}))" , engine)
        data_antejardin         = pd.read_sql_query(f"SELECT codigoid,dimension,nota,observacio FROM  pot.bogota_antejardin WHERE ST_CONTAINS(geometry,Point({longitud},{latitud}))" , engine)

    data_referencia = data_ref_avaluo_terreno.merge(data_ref_avaluo_manzana,on='mancodigo',how='outer')
    engine.dispose()
    return data_referencia,data_antejardin


@st.cache_data(show_spinner=False)
def cargas_fijas_variables(proyecto='CONSTRUCCION',uso='VIVIENDA',vivienda=None,composicion=None,modalidad=None,estrato=None,area=None):

    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    data_carga_fija     = pd.DataFrame()
    data_carga_variable = pd.DataFrame()

    # Carga fija
    if isinstance(area, (float, int)):
        data_carga_fija = pd.read_sql_query(f"SELECT subtotal,iva,total_cargo_fijo FROM urbex.vuc_cargos_fijos WHERE proyecto='{proyecto}' AND uso='{uso}' AND  (vivienda='{vivienda}' OR vivienda IS NULL) AND (composicion='{composicion}' OR composicion IS NULL) AND (estrato={estrato} OR estrato IS NULL) ORDER BY ABS(area - {area}) LIMIT 1" , engine)
    else:
        data_carga_fija = pd.read_sql_query(f"SELECT subtotal,iva,total_cargo_fijo FROM urbex.vuc_cargos_fijos WHERE proyecto='{proyecto}' AND uso='{uso}' AND  (vivienda='{vivienda}' OR vivienda IS NULL) AND (composicion='{composicion}' OR composicion IS NULL) AND (estrato={estrato} OR estrato IS NULL) LIMIT 1" , engine)
    
    # Carga variable
    if isinstance(area, (float, int)):
        data_carga_variable = pd.read_sql_query(f"SELECT subtotal,iva,total_cargo_variable FROM urbex.vuc_cargos_variables WHERE proyecto_input='{proyecto}' AND uso_input='{uso}' AND  (vivienda_input='{vivienda}' OR vivienda_input IS NULL) AND (modalidad_input='{modalidad}' OR modalidad_input IS NULL) AND (estrato_input={estrato} OR estrato_input IS NULL) ORDER BY ABS(area_input - {area}) LIMIT 1" , engine)
    else:
        data_carga_variable = pd.read_sql_query(f"SELECT subtotal,iva,total_cargo_variable FROM urbex.vuc_cargos_variables WHERE proyecto_input='{proyecto}' AND uso_input='{uso}' AND  (vivienda_input='{vivienda}' OR vivienda_input IS NULL) AND (modalidad_input='{modalidad}' OR modalidad_input IS NULL) AND (estrato_input={estrato} OR estrato_input IS NULL) LIMIT 1" , engine)

    return data_carga_fija,data_carga_variable
