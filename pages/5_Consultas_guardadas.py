import streamlit as st
import json
import base64
import urllib.parse
import pandas as pd
from streamlit_js_eval import streamlit_js_eval

from data._principal_historic_search import DataHistoricSearch, barmanpre2grupo
from functions._principal_login import main as login

from display.style_white import style 

try: st.set_page_config(layout="wide",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")
except: pass

def main():
    
    style()

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
        'token': None,
        'access': False
    }
    
    for key, value in formato.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    #-------------------------------------------------------------------------#
    # Login
    if not st.session_state.access:
        with st.spinner('Iniciando sesión...'):
            login()
    #else:
    #    logout()
        
    #-------------------------------------------------------------------------#
    # Ejecutable
    if st.session_state.access:
        
        params = None
        if 'token' in st.query_params: 
            params = st.query_params['token']
    
        if isinstance(params,str) and params!='':
            
            params = f"token={params}"
            params = urllib.parse.parse_qs(params)
            params = params['token'][0]
            params = base64.urlsafe_b64decode(params.encode())
            params = json.loads(params.decode())
        
            if 'token' not in st.session_state:
                st.session_state.token = params['token'] if 'token' in params else None
   
        data          = pd.DataFrame()
        databarmanpre = pd.DataFrame()
        if st.session_state.access and isinstance(st.session_state.token,str):
            with st.spinner('Buscando informacion'):
                data = DataHistoricSearch(token=st.session_state.token)
            
        if not data.empty:
            
            data['seccion_ref'] = data['seccion'].replace({'_detalle_building':'Predios','_busqueda_general':'Búsqueda por mapa','_busqueda_lotes':'Búsqueda de lotes','_combinacion_lote':'Combinación de lotes'})
            data['idmerge']     = range(len(data))
            datapaso            = data[data['barmanpre'].notnull()]
            if not datapaso.empty:
                barmanprelist = set(code for row in datapaso['barmanpre'] for code in row.split("|"))
                barmanprelist = list(barmanprelist)
                databarmanpre, datadirecciones = barmanpre2grupo(barmanprelist)
                
                if not databarmanpre.empty:
                    datapaso_expand = datapaso.assign(barmanpre=datapaso['barmanpre'].str.split('|')).explode('barmanpre')
                    datamerge       = databarmanpre.drop_duplicates(subset='barmanpre',keep='first')
                    datamerge       = datapaso_expand.merge(datamerge, on='barmanpre', how='left',validate='m:1')
                    datamerge       = datamerge.groupby('idmerge').agg({'grupo': lambda x: '|'.join(map(str, x))}).reset_index()
                    data            = data.merge(datamerge,on='idmerge',how='left',validate='m:1')
                    
                if not datadirecciones.empty:
                    
                    d1 = datadirecciones.groupby('barmanpre').agg({'formato_direccion': lambda x: ' | '.join(sorted(set(map(str, x))))}).reset_index() if 'formato_direccion' in datadirecciones else pd.DataFrame()
                    d2 = datadirecciones.groupby('barmanpre').agg({'prenbarrio': lambda x: ' | '.join(sorted(set(map(str, x))))}).reset_index()  if 'prenbarrio' in datadirecciones else pd.DataFrame()
                    datapaso_expand = datapaso.assign(barmanpre=datapaso['barmanpre'].str.split('|')).explode('barmanpre')
                    
                    if not d1.empty:
                        datamerge       = datapaso_expand.merge(d1, on='barmanpre', how='left',validate='m:1')
                        datamerge       = datamerge.groupby('idmerge').agg({'formato_direccion': lambda x: ' | '.join(sorted(set(map(str, x))))}).reset_index()
                        data            = data.merge(datamerge,on='idmerge',how='left',validate='m:1')
                        
                    if not d2.empty:
                        datamerge       = datapaso_expand.merge(d2, on='barmanpre', how='left',validate='m:1')
                        datamerge       = datamerge.groupby('idmerge').agg({'prenbarrio': lambda x: ' | '.join(sorted(set(map(str, x))))}).reset_index()
                        data            = data.merge(datamerge,on='idmerge',how='left',validate='m:1')

                    for j in ['formato_direccion','prenbarrio']:
                       if not data.empty and j not in data:
                           data[j] = ''
                           
        if st.session_state.access and isinstance(st.session_state.token,str):
            htmlrender = htmltable(data)
            st.components.v1.html(htmlrender, height=1000, scrolling=True)
            
        
    
def htmltable(data=pd.DataFrame()):
    
    html_content = 'No se han encontrado consultas guardadas'
    
    if not data.empty:
        #-------------------------------------------------------------------------#
        # Tabla
        #-------------------------------------------------------------------------#
        fulltable = 'style="max-height: 500px; filter: blur(0px); line-height: 1;"'
        
        data['link'] = None
        data['link'] = data.apply(lambda x: params2url_detalle_building(x['grupo'],x['barmanpre'],x['id_consulta'],st.session_state.token) if '_detalle_building' in x['seccion'] else x['link'],axis=1)
        data['link'] = data.apply(lambda x: params2url_busqueda_general(x['inputvar'],x['id_consulta'],st.session_state.token) if '_busqueda_general' in x['seccion'] else x['link'],axis=1)
        data['link'] = data.apply(lambda x: params2url_busqueda_lotes(x['inputvar'],x['id_consulta'],st.session_state.token) if '_busqueda_lotes' in x['seccion'] else x['link'],axis=1)
        data['link'] = data.apply(lambda x: params2url_combinacion_lotes(x['grupo'],x['barmanpre'],x['id_consulta'],st.session_state.token) if '_combinacion_lote' in x['seccion'] else x['link'],axis=1)

        formato_data = [
            {
                'data': data,
                'columns': ['Link','seccion_ref','prenbarrio', 'fecha_consulta','formato_direccion'],
                'rename': {'seccion_ref':'Sección','fecha_consulta':'Fecha de consulta','formato_direccion':'Dirección','prenbarrio':'Barrio catastral'},
                'icon': 'https://iconsapp.nyc3.digitaloceanspaces.com/lupa.png',
                'filtercolumn': 'fecha_consulta',
                'title': 'Consultas guardadas'
            }
        ]
    
        tables_html = ""
        for items in formato_data:
            if not items['data'].empty:
                data = items['data'].sort_values(by=items['filtercolumn'], ascending=items['ascending'] if 'ascending' in items else True)
        
                # Renombrar columnas usando el diccionario 'rename'
                rename_dict = items.get('rename', {})
                columns_with_rename = [rename_dict.get(col, col) for col in items['columns']]
        
                tables_html += f'''
                <section>
                    <div class="urbex-container">
                        <div class="urbex-row urbex-p-3">
                            <div class="urbex-col" style="font-size: 14px;">
                                <h1 id="seccion_title">{items['title']}</h1>
                                <div class="urbex-table-responsive urbex-text-center urbex-shadow" {fulltable}>
                                    <table class="urbex-table urbex-table-striped urbex-table-sm urbex-table-bordered">
                                        <thead class="urbex-bg-primary urbex-text-white" style="font-size: 16px;; position: sticky; top: 0; z-index: 2;">
                                            <tr>
                                                {''.join(f'<th id="table-header-style">{col}</th>' for col in columns_with_rename)}
                                            </tr>
                                        </thead>
                                        <tbody>
                '''
        
                for _, row in data.iterrows():
                    tables_html += "<tr>"
                    for col in items['columns']:
                        if col == 'Link':
                            tables_html += f'''
                                <td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    <a href="{row['link']}" target="_blank">
                                        <img src="{items['icon']}" alt="link" style="width: 16px; height: 16px; object-fit: contain;">
                                    </a>
                                </td>
                            '''
                        elif col == 'cuantia' and isinstance(row.get(col), (int, float)):
                            tables_html += f'''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${row[col]:,.0f}</td>'''
                        elif not pd.isna(row.get(col)):
                            tables_html += f'''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{row.get(col, '')}</td>'''
                        else:
                            tables_html += '''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"></td>'''
                    tables_html += "</tr>"
        
                tables_html += '''
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
                '''
                
                
        html_content = f'''
        <!DOCTYPE html>
        <html data-bs-theme="light" lang="en">
        <head>
          <meta charset="utf-8"/>
          <meta content="width=device-width, initial-scale=1.0, shrink-to-fit=no" name="viewport"/>
          <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_bootstrap.min.css" rel="stylesheet"/>
          <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_styles.css" rel="stylesheet"/>
          <style>
    
            body::-webkit-scrollbar {{
                display: none;
            }}
          </style>
    
        </head>
        <body>
            {tables_html}
        </body>
        </html>
        '''
    
    return html_content
        
def params2url_detalle_building(grupo,barmanpre,id_consulta,token):
    urlexport = "http://localhost:8501/Reporte"
    params    = {'type':'predio','grupo':grupo,'barmanpre':barmanpre,'token':token,'favorito':True,'id_consulta':id_consulta}
    params    = json.dumps(params)
    params    = base64.urlsafe_b64encode(params.encode()).decode()
    params    = urllib.parse.urlencode({'token': params})
    return f"{urlexport}?{params}"
    
def params2url_busqueda_general(inputvar,id_consulta,token):
    urlexport = "http://localhost:8501/Reporte"
    params    = {'type':'busqueda_general','inputvar':inputvar,'token':token,'favorito':True,'id_consulta':id_consulta}
    params    = json.dumps(params)
    params    = base64.urlsafe_b64encode(params.encode()).decode()
    params    = urllib.parse.urlencode({'token': params})
    return f"{urlexport}?{params}"

def params2url_busqueda_lotes(inputvar,id_consulta,token):
    urlexport = "http://localhost:8501/Reporte"
    params    = {'type':'busqueda_lotes','inputvar':inputvar,'token':token,'favorito':True,'id_consulta':id_consulta}
    params    = json.dumps(params)
    params    = base64.urlsafe_b64encode(params.encode()).decode()
    params    = urllib.parse.urlencode({'token': params})
    return f"{urlexport}?{params}"

def params2url_combinacion_lotes(grupo,barmanpre,id_consulta,token):
    #urlexport = "http://localhost:8501/Lotes"
    urlexport = "http://localhost:8501/Reporte"
    params    = {'type':'combinacion_lote','grupo':grupo,'barmanpre':barmanpre,'token':token,'favorito':True,'id_consulta':id_consulta}
    params    = json.dumps(params)
    params    = base64.urlsafe_b64encode(params.encode()).decode()
    params    = urllib.parse.urlencode({'token': params})
    return f"{urlexport}?{params}"


def truncate_list(lst, max_items=3):
    """Trunca la lista a un máximo de `max_items` elementos y añade ' | ...' si hay más."""
    sorted_lst = sorted(set(map(str, lst)))  # Ordenar y eliminar duplicados
    return ' | '.join(sorted_lst[:max_items]) + (' | ...' if len(sorted_lst) > max_items else '')

if __name__ == "__main__":
    main()