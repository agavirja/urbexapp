import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def getlicencias(barmanpre):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
   
    data     = pd.DataFrame()
    html     = ""
    tableH   = 100
    if isinstance(barmanpre,str) and barmanpre!='':
        data = pd.read_sql_query(f"SELECT * FROM  {schema}.data_bogota_licencias WHERE barmanpre LIKE '%{barmanpre}%'" , engine)
    elif isinstance(barmanpre, list):
        query = ' OR '.join([f'barmanpre LIKE "%{item}%"' for item in barmanpre])
        data = pd.read_sql_query(f"SELECT * FROM  {schema}.data_bogota_licencias WHERE {query}" , engine)
    engine.dispose()
    
    if not data.empty:
        
        if   len(data)>=10: tableH = 450
        elif len(data)>=5:  tableH = int(len(data)*45)
        elif len(data)>1:   tableH = int(len(data)*60)
        elif len(data)==1:  tableH = 100
        else: tableH = 100
            
        html_paso = ""
        for _,items in data.iterrows():
            
            try:    curaduria = f"{int(items['curaduria'])}"
            except: curaduria = ''    
            licencia     = items['licencia'] if 'licencia' in items and isinstance(items['licencia'],str) else ""
            propietarios = items['propietarios'] if 'propietarios' in items and isinstance(items['propietarios'],str) else ""
            proyecto     = items['proyecto'] if 'proyecto' in items and isinstance(items['proyecto'],str) else ""
            tramite      = items['tramite'] if 'tramite' in items and isinstance(items['tramite'],str) else ""
            estado       = items['estado'] if 'estado' in items and isinstance(items['estado'],str) else "" 
            fecha        = items['fecha'] if 'fecha' in items and isinstance(items['fecha'],str) else "" 
            year         = ""
            try:
                shortyear = str(fecha).split('-')[0]
                if len(shortyear)==4 and isinstance(int(shortyear),int):
                    year = f"{shortyear}"
            except: year = ""
            if year=="":
                try: 
                    shortyear = items['licencia'].split('-')[2]
                    if len(shortyear)==2 and isinstance(int(shortyear),int):
                        year = f"20{shortyear}"
                except: pass
            
            html_paso += f"""
            <tr>
                <td>{curaduria}</td>    
                <td>{licencia}</td>
                <td>{propietarios}</td>    
                <td>{proyecto}</td>    
                <td>{tramite}</td>    
                <td>{estado}</td>    
                <td>{year}</td>    
                <td>{fecha}</td> 
            </tr>
            """
        html_paso = f"""
        <thead>
            <tr>
                <th>Curaduría</th>
                <th>Licencia</th>
                <th>Propietarios</th>
                <th>Proyecto</th>
                <th>Tramite</th>
                <th>Estado</th>
                <th>Año</th>
                <th>Fecha</th>
            </tr>
        </thead>
        <tbody>
        {html_paso}
        </tbody>
        """
        style = tablestyle()
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {style}
        </head>
        <body>
            <div class="table-wrapper table-background">
                <div class="table-scroll">
                    <table class="fl-table">
                    {html_paso}
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
    return data,html,tableH

@st.cache_data
def tablestyle():
    return """
        <style>
            * {
                box-sizing: border-box;
                -webkit-box-sizing: border-box;
                -moz-box-sizing: border-box;
            }
        
            body {
                font-family: Helvetica;
                -webkit-font-smoothing: antialiased;
            }
        
            .table-background {
                background: rgba(71, 147, 227, 1);
            }
        
            h2 {
                text-align: center;
                font-size: 18px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: white;
                padding: 30px 0;
            }
        
            /* Table Styles */
        
            .table-wrapper {
                margin: 10px 70px 70px;
                box-shadow: 0px 35px 50px rgba(0, 0, 0, 0.2);
            }
        
            .fl-table {
                border-radius: 5px;
                font-size: 12px;
                font-weight: normal;
                border: none;
                border-collapse: collapse;
                width: 100%;
                max-width: 100%;
                white-space: nowrap;
                background-color: white;
            }
        
            .fl-table td,
            .fl-table th {
                text-align: center;
                padding: 8px;
            }
        
            .fl-table td {
                border-right: 1px solid #f8f8f8;
                font-size: 12px;
            }
        
            .fl-table thead th {
                color: #ffffff;
                background: #A16CFF; /* Manteniendo el color verde claro para el encabezado */
                position: sticky; /* Haciendo el encabezado fijo */
                top: 0; /* Fijando el encabezado en la parte superior */
            }
        
            .fl-table tr:nth-child(even) {
                background: #f8f8f8;
            }
            .table-scroll {
                overflow-x: auto;
                overflow-y: auto;
                max-height: 400px; /* Altura máxima ajustable según tus necesidades */
            }
        
            @media (max-width: 767px) {
                .fl-table {
                    display: block;
                    width: 100%;
                }
                .table-wrapper:before {
                    content: "Scroll horizontally >";
                    display: block;
                    text-align: right;
                    font-size: 11px;
                    color: white;
                    padding: 0 0 10px;
                }
                .fl-table thead,
                .fl-table tbody,
                .fl-table thead th {
                    display: block;
                }
                .fl-table thead th:last-child {
                    border-bottom: none;
                }
                .fl-table thead {
                    float: left;
                }
                .fl-table tbody {
                    width: auto;
                    position: relative;
                    overflow-x: auto;
                }
                .fl-table td,
                .fl-table th {
                    padding: 20px .625em .625em .625em;
                    height: 60px;
                    vertical-align: middle;
                    box-sizing: border-box;
                    overflow-x: hidden;
                    overflow-y: auto;
                    width: 120px;
                    font-size: 13px;
                    text-overflow: ellipsis;
                }
                .fl-table thead th {
                    text-align: left;
                    border-bottom: 1px solid #f7f7f9;
                }
                .fl-table tbody tr {
                    display: table-cell;
                }
                .fl-table tbody tr:nth-child(odd) {
                    background: none;
                }
                .fl-table tr:nth-child(even) {
                    background: transparent;
                }
                .fl-table tr td:nth-child(odd) {
                    background: #f8f8f8;
                    border-right: 1px solid #e6e4e4;
                }
                .fl-table tr td:nth-child(even) {
                    border-right: 1px solid #e6e4e4;
                }
                .fl-table tbody td {
                    display: block;
                    text-align: center;
                }
            }
        </style>
        """
