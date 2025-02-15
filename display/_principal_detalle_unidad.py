import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime

def main(data_predio=pd.DataFrame(), data_prediales=pd.DataFrame(), data_transacciones=pd.DataFrame(), data_usosuelopredios=pd.DataFrame(), pdfversion=False):

    if not data_prediales.empty:
        data_prediales['link'] = data_prediales['url'] if 'url' in data_prediales else ''
        idd = data_prediales['link'].isnull() if 'link' in data_prediales else 0
        if sum(idd)>0:
            if 'yearmax' in data_prediales:
                data_prediales.loc[idd,'link'] = data_prediales.loc[idd].apply(lambda x: getlink(x['yearmax'],x['chip']),axis=1)

    info_catastral     = data_prediales[data_prediales['year']==data_prediales['year'].max()] if not data_prediales.empty and 'year' in data_prediales else pd.DataFrame(columns=['nombre','copropiedad','tipoPropietario','tipoDocumento','identificacion','telefonos','email'])
    info_transacciones = data_transacciones[data_transacciones['codigo'].isin(['125','126','164','168','169','0125','0126','0164','0168','0169'])] if not data_transacciones.empty  else pd.DataFrame(columns=['titular','tipoPropietario','tipoDocumento','identificacion','telefonos','email'])
    
    #-------------------------------------------------------------------------#
    # Información propietarios 
    #-------------------------------------------------------------------------#
    infopropietarios = pd.DataFrame() 
    if not info_catastral.empty: 
        infopropietarios       = info_catastral[['nombre','copropiedad','tipoPropietario','tipoDocumento','identificacion','telefonos','email']]
        infopropietarios       = infopropietarios.drop_duplicates()
        infopropietarios.index = range(len(infopropietarios))
        if len(infopropietarios)>1:
            labelpropietarios       = pd.DataFrame([{None:f'Propietario {x+1}:'} for x in range(len(infopropietarios))])
            labelpropietarios.index = range(len(labelpropietarios))
            infopropietarios        = labelpropietarios.merge(infopropietarios,left_index=True,right_index=True)
        
        infopropietarios.rename(columns={'nombre':'Nombre:','copropiedad':'Copropiedad (%):','tipoPropietario':'Tipo:','tipoDocumento':'Tipo documento:','identificacion':'Identificación:','telefonos':'Teléfonos:','email':'Email:'},inplace=True)
        infopropietarios['numero'] = range(len(infopropietarios))
        infopropietarios           = infopropietarios.melt(id_vars=["numero"], var_name="titulo", value_name="valor")
        infopropietarios['orden']  = range(len(infopropietarios))
        infopropietarios           = infopropietarios.sort_values(by=['numero','orden'],ascending=True)


    #-------------------------------------------------------------------------#
    # Información propietarios transacciones
    #-------------------------------------------------------------------------#
    infopropietariossnr = pd.DataFrame() 
    if not info_transacciones.empty: 
        info_transacciones        = info_transacciones[info_transacciones['fecha_documento_publico']==info_transacciones['fecha_documento_publico'].max()]
        infopropietariossnr       = info_transacciones[['titular','tipoPropietario','tipoDocumento','nrodocumento','telefonos','email']]
        infopropietariossnr       = infopropietariossnr.drop_duplicates()
        infopropietariossnr.index = range(len(infopropietariossnr))
        if len(infopropietariossnr)>1:
            labelpropietarios       = pd.DataFrame([{None:f'Propietario {x+1}:'} for x in range(len(infopropietariossnr))])
            labelpropietarios.index = range(len(labelpropietarios))
            infopropietariossnr        = labelpropietarios.merge(infopropietariossnr,left_index=True,right_index=True)
        
        infopropietariossnr.rename(columns={'titular':'Nombre:','tipoPropietario':'Tipo:','tipoDocumento':'Tipo documento:','nrodocumento':'Identificación:','telefonos':'Teléfonos:','email':'Email:'},inplace=True)
        infopropietariossnr['numero'] = range(len(infopropietariossnr))
        infopropietariossnr           = infopropietariossnr.melt(id_vars=["numero"], var_name="titulo", value_name="valor")
        infopropietariossnr['orden']  = range(len(infopropietariossnr))
        infopropietariossnr           = infopropietariossnr.sort_values(by=['numero','orden'],ascending=True)

      
    #-------------------------------------------------------------------------#
    # Información General
    #-------------------------------------------------------------------------#
    formato = [{'seccion':'Información del predio','items':[
                {'titulo':'Dirección:','valor':data_predio['predirecc'].iloc[0] if not data_predio.empty and 'predirecc' in data_predio else None},
                {'titulo':'Chip:','valor':data_predio['prechip'].iloc[0] if not data_predio.empty and 'prechip' in data_predio else None},
                {'titulo':'Matrícula Inmobiliaria:','valor':data_predio['matriculainmobiliaria'].iloc[0] if not data_predio.empty and 'matriculainmobiliaria' in data_predio else None},
                {'titulo':'Cédula catastral:','valor':data_predio['precedcata'].iloc[0] if not data_predio.empty and 'precedcata' in data_predio else None},
                {'titulo':'Área privada:','valor':data_predio['preaconst'].iloc[0] if not data_predio.empty and 'preaconst' in data_predio else None},
                {'titulo':'Área de terreno','valor':data_predio['preaterre'].iloc[0] if not data_predio.empty and 'preaterre' in data_predio else None},
                {'titulo':'Uso:','valor':data_predio['usosuelo'].iloc[0] if not data_predio.empty and 'usosuelo' in data_predio else None},
                {'titulo':'Predios (mismo uso):','valor':data_usosuelopredios['predios_precuso'].iloc[0] if not data_usosuelopredios.empty and 'predios_precuso' in data_usosuelopredios else None},
                ]},
        
                {'seccion':'Información Catastral','items':[
                            {'titulo':'Vigencia:','valor':int(info_catastral['year'].max()) if 'year' in info_catastral and isinstance(info_catastral['year'].max(),(int,float)) else ''},
                            {'titulo':'Avalúo Catastral:','valor':f"${info_catastral['avaluo_catastral'].iloc[0]:,.0f}" if not info_catastral.empty and 'avaluo_catastral' in info_catastral and not pd.isna(info_catastral['avaluo_catastral'].iloc[0]) else None},
                            {'titulo':'Impuesto Predial:','valor':f"${info_catastral['impuesto_predial'].iloc[0]:,.0f}" if not info_catastral.empty and 'impuesto_predial' in info_catastral and not pd.isna(info_catastral['impuesto_predial'].iloc[0]) else None },
                            {'titulo':'Descargar predial:','valor':
                             f"""
                            <a href="{info_catastral['link'].iloc[0]}" target="_blank">
                                <img src="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png" alt="link" style="width: 16px; height: 16px; object-fit: contain;">
                            </a>
                             """},
                            ]},
                             
                {'seccion':'Propietarios (según predial)','items':infopropietarios[['titulo','valor']].to_dict(orient='records')  if not infopropietarios.empty and all([x for x in ['titulo','valor'] if x in infopropietarios]) else [] },
                
                {'seccion':f'Propietarios (según transacciones a partir de {datetime.now().year})','items':infopropietariossnr[['titulo','valor']].to_dict(orient='records')  if not infopropietariossnr.empty and all([x for x in ['titulo','valor'] if x in infopropietariossnr]) else []},
                
            ]
    

    sections_html = """
    <div class="urbex-col-12 urbex-col-sm-12 urbex-col-md-12 urbex-col-lg-4 urbex-col-xl-4 urbex-col-xxl-4 urbex-p-4">
    """
    for section in formato:
        section_title = section["seccion"]
        items = section["items"]
        
        # Determinar si la sección contiene listas verificando el primer item
        contains_list = any(isinstance(item.get("valor"), list) for item in items)
        
        if not contains_list and isinstance(items,list) and items!=[]:
            sections_html += f'''
            <div class="urbex-row" style="margin-bottom: 20px;">
                <div class="urbex-col">
                    <div class="urbex-h-100 urbex-p-3" id="box_shadow_default">
                        <h1 class="urbex-mt-2" id="title_inside_table">{section_title}</h1>
                        <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.5;">
                            <table class="urbex-table urbex-table-sm urbex-table-borderless">
                                <tbody>
            '''
            for item in items:
                value  = item["valor"] if "valor" in item else None
                value  = 'Sin información' if value is None else value
                titulo = item["titulo"] if 'titulo' in item else ''
                
                is_empty    = True if "titulo" in item and ((isinstance(item["titulo"],str) and item["titulo"]=='') or item["titulo"] is None) else False
                title_style = 'color: #666666; font-weight: bold;' if is_empty else ''
                if is_empty:
                    sections_html += """<tr><td colspan="2" style="padding: 0.5rem;"></td></tr>"""
                    titulo         = value
                    value          = ''
                
                sections_html += f'''
                                <tr>
                                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;">
                                        <span id="label_inside" style="{title_style}">{titulo}</span>
                                    </td>
                                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;">
                                        <span id="value_inside">{value}</span>
                                    </td>
                                </tr>'''
            
            sections_html += '''
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            '''
        
    sections_html += '''
    </div>
    '''
    #-------------------------------------------------------------------------#
    # Grafica 
    #-------------------------------------------------------------------------#
    style_chart = ""
    try:    
        df = data_prediales.copy()
        df = df[df['year']>2018]
        df = df[(df['avaluo_catastral'].notnull()) & (df['impuesto_predial'].notnull()) ]
        if not df.empty:
            df = df.groupby(['year']).agg({'avaluo_catastral':'max','impuesto_predial':'max'}).reset_index()
            df.columns  = ['year','valor1','valor2']
            style_chart += double_axis_chart(df,'PredialChart')
    except: pass

    #-------------------------------------------------------------------------#
    # Tablas 
    #-------------------------------------------------------------------------#
    fulltable = 'style="max-height: 400px;filter: blur(0px);line-height: 1;margin-bottom: 20px;font-size: 12px;text-align: center;"'
    if pdfversion: fulltable = ''
    
    data_prediales = data_prediales.sort_values(by=['chip','year','url'],ascending=False,na_position='last')   

    data_transacciones['link'] = data_transacciones['docid'].apply(
        lambda x: f"https://radicacion.supernotariado.gov.co/app/static/ServletFilesViewer?docId={x}"
    ) if 'docid' in data_transacciones else ''


    if 'fecha_documento_publico' in data_transacciones:
        data_transacciones['fecha_documento_publico'] = pd.to_datetime(data_transacciones['fecha_documento_publico'], unit='ms')
        data_transacciones = data_transacciones.sort_values(by='fecha_documento_publico',ascending=False)
        
    for i in ['year']:
        if i in data_prediales:
            data_prediales['year'] = data_prediales['year'].apply(lambda x: int(x) if isinstance(x,(int,float)) else None)
        
    if not data_prediales.empty and 'copropiedad' in data_prediales:
        data_prediales['copropiedad'] = data_prediales['copropiedad'].apply(lambda x: '' if pd.isna(x) or x=='' else (int(float(x)) if float(x).is_integer() else round(float(x), 1)))
        
    formato_data = [
        {
            'data': data_prediales,
            'columns': ['Link', 'direccion', 'year', 'avaluo_catastral', 'impuesto_predial', 'preaconst', 'chip','matriculainmobiliaria','tipoPropietario','tipoDocumento','nombre','identificacion','copropiedad','indPago'],
            'rename': {'direccion':'Dirección', 'year':'Año', 'avaluo_catastral':'Avalúo catastral', 'impuesto_predial':'Predial', 'preaconst':'Área construida', 'chip':'Chip','matriculainmobiliaria':'Matrícula inmobiliaria','tipoPropietario':'Tipo de propietario','tipoDocumento':'Tipo documento','nombre':'Propietario','identificacion':'Identificación','copropiedad':'Copropiedad','indPago':'Indicador de pago'},
            'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
            'filtercolumn': 'predirecc',
            'title': 'Prediales / Avalúos catastrales'
        },
        {
            'data': data_transacciones,
            'columns': ['Link', 'predirecc', 'fecha_documento_publico', 'codigo', 'nombre', 'cuantia', 'entidad', 
                       'numero_documento_publico', 'oficina', 'preaconst', 'preaterre', 'chip', 'usosuelo', 
                       'tipo_documento_publico', 'titular', 'email', 'tipo', 'nrodocumento'],
            'rename': {'chip':'Chip','codigo':'Código', 'cuantia':'Cuantía', 'entidad':'Entidad', 'fecha_documento_publico':'Fecha', 'nombre':'Tipo', 
                       'numero_documento_publico':'Número escritura', 'oficina':'Oficina', 'preaconst':'Área Construida', 'preaterre':'Área de Terreno', 'usosuelo':'Uso del suelo', 'predirecc':'Dirección', 
                       'tipo_documento_publico':'Tipo de documento', 'titular':'Titular', 'email':'Email', 'tipo':'Tipo documento', 'nrodocumento':'Número documento'},
            'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
            'filtercolumn': 'fecha_documento_publico',
            'ascending':False,
            'title': 'Transacciones / Anotaciones'
        }
    ]
    
    tables_html = ""
    for items in formato_data:
        if not items['data'].empty:
            # Título de la tabla
            tables_html += f'''
            <div class="urbex-row">
                <div class="urbex-col">
                    <h1 id="seccion_title_tabla">{items['title']}</h1>
                </div>
            </div>
            '''
            
            # Contenedor de la tabla
            tables_html += '''
            <div class="urbex-row">
                <div class="urbex-col" id="box_shadow_default" style="padding: 20px;margin-bottom: 20px;">
                    <style>
                        .custom-urbex-table {
                            width: auto;
                            table-layout: auto;
                        }
                        .custom-urbex-table td,
                        .custom-urbex-table th {
                            width: 100%;
                            white-space: nowrap;
                            overflow: hidden;
                            text-overflow: ellipsis;
                        }
                    </style>
                    <div class="urbex-table-responsive urbex-text-center" {fulltable}>
                        <table class="urbex-table custom-urbex-table urbex-table-striped urbex-table-sm">
                            <thead style="font-size: 16px; position: sticky; top: 0; z-index: 2;">
                                <tr>
            '''
            
            # Encabezados de la tabla con los nombres renombrados
            renamed_columns = [items['rename'].get(col, col) for col in items['columns']]  # Renombrar columnas según el diccionario
            tables_html += ''.join(f'<th id="table-header-style">{col}</th>' for col in renamed_columns)
            
            tables_html += '''
                                </tr>
                            </thead>
                            <tbody>
            '''
            
            # Filas de datos
            data = items['data']
            for _, row in data.iterrows():
                tables_html += "<tr>"
                for col in items['columns']:
                    if col == 'Link':
                        tables_html += f'''
                            <td>
                                <a href="{row['link']}" target="_blank">
                                    <img src="{items['icon']}" alt="link" style="width: 16px; height: 16px; object-fit: contain;">
                                </a>
                            </td>
                        '''
                    elif any([x for x in ['cuantia','avaluo_catastral','impuesto_predial'] if col in x]) and not pd.isna(row.get(col)) and isinstance(row.get(col), (int, float)):
                        tables_html += f"<td>${row[col]:,.0f}</td>"
                    else:
                        value = row.get(col, '')
                        value = '' if pd.isna(value) else value
                        tables_html += f"<td>{value}</td>"
                tables_html += "</tr>"
            
            tables_html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            '''

    #-------------------------------------------------------------------------#
    # CSS y HTML final
    #-------------------------------------------------------------------------#
    html_content = f'''
    <!DOCTYPE html>
    
    <html data-bs-theme="light" lang="en">
    <head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0, shrink-to-fit=no" name="viewport"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_bootstrap.min.css" rel="stylesheet"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_styles.css" rel="stylesheet"/>
    <style>
        /* Reducir tamaño de la fuente dentro de las tablas */
        .urbex-table td, .urbex-table th {{
            font-size: 10px;  
        }}
        
        .urbex-table {{
          width: 100%;
          table-layout: fixed; 
        }}
        
        td, th {{
          width: 100%;
          word-wrap: break-word; 
          white-space: normal; 
        }}
        
    </style>
    </head>
    <body>
    <section>
     <div class="urbex-container-fluid">
      <div class="urbex-row">
       <div class="urbex-container-fluid">
        <div class="urbex-row">
        
        {sections_html}
         
         
         <div class="urbex-col-12 urbex-col-sm-12 urbex-col-md-12 urbex-col-lg-8 urbex-col-xl-8 urbex-col-xxl-8">
          <div class="urbex-row" style="min-height: 300px;">
           <div class="urbex-col" id="box_shadow_default" style="padding: 20px;margin-bottom: 20px;">
            <div>
             <canvas id="PredialChart" style="height: 300px;"></canvas>
            </div>
           </div>
          </div>
          {tables_html}
         </div>
         
        </div>
       </div>
      </section>
    {style_chart}
    <script src="assets/bootstrap/js/bootstrap.min.js"></script>
    </body>
    </html>
    '''
    
    return html_content

def double_axis_chart(df,name):
    return f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
    
    <canvas id="{name}" width="400" height="400"></canvas>
    <script>
    Chart.register(ChartDataLabels);
    var ctx = document.getElementById('{name}').getContext('2d');
    var {name} = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: {df['year'].tolist()},
            datasets: [{{
                label: 'Avalúo catastral',
                data: {df['valor1'].tolist()},
                yAxisID: 'A',
                backgroundColor: 'rgba(0, 123, 255, 0.8)',
                borderColor: 'rgba(0, 123, 255, 1)',
                borderWidth: 1
            }}, {{
                label: 'Impuesto predial',
                data: {df['valor2'].tolist()},
                yAxisID: 'B',
                backgroundColor: 'rgba(153, 102, 255, 0.8)',
                borderColor: 'rgba(153, 102, 255, 1)',
                borderWidth: 1
            }}]
        }},
        options: {{
            plugins: {{
                datalabels: {{
                    color: 'white',
                    anchor: 'center',
                    align: 'center',
                    rotation: -90,
                    font: {{
                        weight: 'bold',
                        size: 10
                    }},
                    formatter: function(value, context) {{
                        return Math.round(value).toLocaleString();
                    }},
                    display: function(context) {{
                        var index = context.dataIndex;
                        var value = context.dataset.data[index];
                        var maxValue = Math.max(...context.dataset.data);
                        return value / maxValue > 0.1;  // Mostrar solo si el valor es más del 10% del máximo
                    }}
                }},
                legend: {{
                    display: true,
                    position: 'bottom',
                    align: 'center',
                    labels: {{
                        boxWidth: 20,
                        padding: 15,
                    }}
                }}
            }},
            scales: {{
                A: {{
                    type: 'linear',
                    position: 'left',
                    grid: {{ display: false }},
                    title: {{
                        display: false
                    }},
                    ticks: {{
                        callback: function(value, index, values) {{
                            return Math.round(value).toLocaleString();
                        }}
                    }}
                }},
                B: {{
                    type: 'linear',
                    position: 'right',
                    grid: {{ display: false }},
                    title: {{
                        display: false
                    }},
                    ticks: {{
                        callback: function(value, index, values) {{
                            return Math.round(value).toLocaleString();
                        }}
                    }}
                }},
                x: {{
                    grid: {{ display: false }},
                    title: {{
                        display: false
                    }}
                }}
            }},
            responsive: true,
            maintainAspectRatio: false,
            title: {{
                display: true,
                text: 'Gráfico de Transacciones y Valores por Año',
                position: 'bottom',
                align: 'start',
                font: {{
                    size: 16
                }}
            }}
        }}
    }});
    </script>
    """
    
    
def generar_codigo(x):
    hash_sha256 = hashlib.sha256(x.encode()).hexdigest()
    codigo      = hash_sha256[:12]
    return codigo

def getlink(year,chip):
    
    REGION      = 'nyc3'
    BUCKET_NAME = 'prediales'
    link        = None 
    try:    
        year = int(year)
        if isinstance(year,int) and isinstance(chip,str) and chip!='':
            codigo = generar_codigo(f'{year}{chip}{year}').upper()
            link   = f'https://{BUCKET_NAME}.{REGION}.digitaloceanspaces.com/{codigo}.pdf'
    except: pass
    
    return link
