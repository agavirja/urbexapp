import pandas as pd
import streamlit as st
import hashlib

def main(data_propietarios=pd.DataFrame()):

    #-------------------------------------------------------------------------#
    # Tablas 
    #-------------------------------------------------------------------------#
    idd = data_propietarios['link'].isnull() if 'link' in data_propietarios else 0
    if sum(idd)>0:
        if 'yearmax' in data_propietarios:
            data_propietarios.loc[idd,'link'] = data_propietarios.loc[idd].apply(lambda x: getlink(x['yearmax'],x['chip']),axis=1)
      
    if 'year' in data_propietarios: 
        data_propietarios['year'] = data_propietarios['year'].apply(lambda x: int(x) if isinstance(x,(int,float)) else '')
    if not data_propietarios.empty and 'copropiedad' in data_propietarios:
        data_propietarios['copropiedad'] = data_propietarios['copropiedad'].apply(lambda x: '' if pd.isna(x) or x=='' else (int(float(x)) if float(x).is_integer() else round(float(x), 1)))
        
    formato_data = [
        {
            'data': data_propietarios,
            'columns': ['link','direccion','year','avaluo_catastral','impuesto_predial','copropiedad','preaconst','preaterre','matriculainmobiliaria','chip','tipoPropietario','tipoDocumento','identificacion','nombre','telefonos','email'],
            'rename': {'link': 'Link', 'direccion': 'Dirección', 'chip': 'Chip', 'avaluo_catastral': 'Avalúo Catastral', 'impuesto_predial': 'Impuesto Predial', 'copropiedad': 'Copropiedad', 'preaconst': 'Área construida', 'preaterre': 'Área de terreno', 'tipoPropietario': 'Tipo de Propietario', 'tipoDocumento': 'Tipo de Documento', 'identificacion': 'Identificación', 'nombre': 'Nombre', 'telefonos': 'Teléfonos', 'email': 'Correo Electrónico', 'matriculainmobiliaria': 'Matrícula inmobiliaria', 'cedula_catastral': 'Cédula catastral', 'year': 'Año', 'tipo': 'Tipo de documento'},
            'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
            'title': 'Propietarios',
            'filtercolumn': 'direccion',
            'ascending':True,
        },
    ]
    
    tables_html = ""
    for items in formato_data:
        if not items['data'].empty:
            data = items['data'].sort_values(by=items['filtercolumn'], ascending=items['ascending'] if 'ascending' in items else True)

            variables = [x for x in items['columns'] if x in data]
            data      = data[variables]
            
            
            # Renombrar las columnas si 'rename' está presente
            if 'rename' in items:
                data = data.rename(columns=items['rename'])
                items['columns'] = list(data.columns)  # Actualizar las columnas después del rename
            
            tables_html += f'''
            <section>
                <div class="urbex-container">
                    <div class="urbex-row urbex-p-3">
                        <div class="urbex-col" style="font-size: 14px;">
                            <h1 id="seccion_title">{items['title']}</h1>
                            <div class="urbex-table-responsive urbex-text-center urbex-shadow" style="max-height: 500px; filter: blur(0px); line-height: 1;">
                                <table class="urbex-table urbex-table-striped urbex-table-sm urbex-table-bordered">
                                    <thead class="urbex-bg-primary urbex-text-white" style="font-size: 16px; position: sticky; top: 0; z-index: 2;">
                                        <tr>
                                            {''.join(f'<th id="table-header-style">{col}</th>' for col in items['columns'])}
                                        </tr>
                                    </thead>
                                    <tbody>
            '''
            
            for _, row in data.iterrows():
                tables_html += "<tr>"
                for col in items['columns']:
                    if col == 'Link':
                        tables_html += f'''
                            <td>
                                <a href="{row['Link']}" target="_blank">
                                    <img src="{items['icon']}" alt="Link" style="width: 16px; height: 16px; object-fit: contain;">
                                </a>
                            </td>
                        '''
                    elif any([x for x in ['Avalúo Catastral','Impuesto Predial'] if col in x]) and not pd.isna(row.get(col)) and isinstance(row.get(col), (int, float)):
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
                </div>
            </section>
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

        .urbex-table th, .urbex-table td {{
            white-space: nowrap;
            min-width: fit-content;
            padding: 0.5rem !important;
        }}
        
        .urbex-table-wrapper {{
            overflow-x: auto;
            width: 100%;
        }}

        .urbex-table thead {{
            position: sticky;
            top: 0;
            z-index: 1;
        }}
        
        body {{
            background-color: #fff;
        }}

        @media screen and (max-width: 767px) {{
            .urbex-table {{
                font-size: 11px;
            }}
            
            .urbex-table thead th {{
                font-size: 12px;
            }}
            
            .urbex-table tbody td {{
                font-size: 11px;
            }}
            
            #label_inside {{
                font-size: 11px;
            }}
            
            #value_inside {{
                font-size: 11px;
            }}
        }}
        
        @media screen and (min-width: 768px) and (max-width: 991px) {{
            .urbex-table {{
                font-size: 12px;
            }}
            
            .urbex-table thead th {{
                font-size: 13px;
            }}
            
            .urbex-table tbody td {{
                font-size: 12px;
            }}
            
            #label_inside {{
                font-size: 12px;
            }}
            
            #value_inside {{
                font-size: 12px;
            }}
        }}
        
        @media screen and (min-width: 992px) {{
            .urbex-table {{
                font-size: 12px;
            }}
            
            .urbex-table thead th {{
                font-size: 12px;
            }}
            
            .urbex-table tbody td {{
                font-size: 11px;
            }}
            
            #label_inside {{
                font-size: 11px;
            }}
            
            #value_inside {{
                font-size: 11px;
            }}
        }}
        
        @media screen and (min-width: 1200px) {{
            .urbex-table {{
                font-size: 14px;
            }}
            
            .urbex-table thead th {{
                font-size: 15px;
            }}
            
            .urbex-table tbody td {{
                font-size: 14px;
            }}
            
            #label_inside {{
                font-size: 14px;
            }}
            
            #value_inside {{
                font-size: 14px;
            }}
        }}    
                             
    </style>
    </head>
    <body>
        <div class="urbex-container">
            <div class="urbex-row">
                <div class="urbex-col-12 urbex-col-sm-12 urbex-col-md-12 urbex-col-lg-12 urbex-col-xl-12 urbex-col-xxl-12">
                    {tables_html}
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html_content

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