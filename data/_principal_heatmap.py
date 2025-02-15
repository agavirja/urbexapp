import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine 
from matplotlib.colors import to_hex

@st.cache_data(show_spinner=False)
def main(year=2024,formato='grid',precuso=[],tipoconsulta=None):
    
    data = get_data_heatmap(year=year,formato=formato,precuso=precuso)
    
    if not data.empty:
        data['prod']  = data['transacciones']*data['valormt2_transacciones']
        data          = data.groupby('id_map').agg({'transacciones':'sum','valormt2_transacciones':'median','prod':'sum','wkt':'first','scanombre':'first'}).reset_index()
        data.columns  = ['id_map','transacciones','valormt2_transacciones','prod','wkt','scanombre']
        data['valormt2_transacciones'] = data['prod']/data['transacciones']
        data['color'] = '#5A189A'

    #---------#
    # Colores #
    label = pd.DataFrame(columns=['pos','color','value'])
    try:
        data['normvalue'] = data[tipoconsulta].rank(pct=True)
        cmap = plt.cm.RdYlGn.reversed() # plt.cm.RdYlGn - plt.cm.viridis
        data['color'] = data['normvalue'].apply(lambda x: to_hex(cmap(x)))
        
        label  = []
        conteo = 0
        for j in [0,0.2,0.4,0.6,0.8,1]:
            conteo    += 1
            df         = data.copy()
            df['diff'] = abs(j-df['normvalue'])
            df         = df.sort_values(by='diff',ascending=True)
            color      = df['color'].iloc[0]
            value      = df[tipoconsulta].iloc[0]
            if 'valormt2_transacciones' in tipoconsulta: 
                value = f"${value /1000000:,.2f} mm"
            elif 'transacciones' in tipoconsulta:
                value = f'{value}    '
            label.append({'pos':conteo,'color':color,'value':value})
        label = pd.DataFrame(label) 
    except: pass
    return data,label
    
    
@st.cache_data(show_spinner=False)
def get_data_heatmap(year=2024,formato='grid',precuso=[]):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    query = ""
    if year is not None and (isinstance(year, float) or isinstance(year, int)):
        query += f" AND year = {year}"

    if isinstance(formato, str):
        query += f" AND type ='{formato}'"
     
    if isinstance(precuso, list) and precuso!=[]:
        lista = "','".join(list(set(precuso)))
        query += f" AND precuso IN ('{lista}')"

    if query!="":
        query = query.strip().strip('AND')
        query = f" WHERE {query}"

    data  = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_heatmap_transacciones {query}" , engine)
    
    if not data.empty:
        lista = "','".join(data['id_map'].astype(int).astype(str).unique())
        query = f" id_map IN ('{lista}') AND type ='{formato}'"
        datashape  = pd.read_sql_query(f"SELECT id_map, ST_AsText(geometry) as wkt FROM  bigdata.bogota_heatmap_shape WHERE {query}" , engine)
        if not datashape.empty:
            datamerge = datashape.drop_duplicates(subset='id_map',keep='first')
            data      = data.merge(datamerge,on='id_map',how='left',validate='m:1')
            
    engine.dispose()
    return data