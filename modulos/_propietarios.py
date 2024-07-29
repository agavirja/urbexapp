import re
import streamlit as st
import pandas as pd
import hashlib

from data.getdatabuilding import main as getdatabuilding

def main(chip=None,barmanpre=None,vartype=None,infilter=True,descargar=True):
    
    html,datavigencia_predio = gethtml(chip=chip,barmanpre=barmanpre,vartype=vartype,infilter=infilter,descargar=descargar) 
    st.components.v1.html(html,height=450)    
    
    if descargar:
        col1,col2,col3 = st.columns([0.7,0.2,0.1])
        with col2:
            st.write('')
            st.write('')
            if st.button('Descargar Excel'):
                download_excel(datavigencia_predio)
    
def gethtml(chip=None,barmanpre=None,vartype=None,infilter=True,descargar=True):
    
    col1,col2,col3,col4  = st.columns([0.1,0.4,0.3,0.2],gap="small")
    chip_referencia     = chip
    html                = ""
    datavigencia_predio = pd.DataFrame()
    if isinstance(barmanpre, str) or isinstance(barmanpre, list):
        with st.spinner('Buscando información'):
            datacatastro,datausosuelo,datalote,datavigencia,datatransacciones,datactl = getdatabuilding(barmanpre)
            
        if not datavigencia.empty: 
            datavigencia['link']  = datavigencia.apply(lambda x: linkPredial(x['chip'],x['vigencia'],x['idSoporteTributario']),axis=1)
            datavigencia['name']  = datavigencia.apply(lambda x: buildname(x['primerNombre'],x['segundoNombre'],x['primerApellido'],x['segundoApellido']),axis=1)
            varphones             = [x for x in ['telefono1','telefono2','telefono3','telefono4','telefono5'] if x in datavigencia]
            datavigencia['phone'] = datavigencia[varphones].apply(buildphone, axis=1)
            varemails             = [x for x in ['email1','email2'] if x in datavigencia]
            datavigencia['email'] = datavigencia[varemails].apply(buildemail, axis=1)
            
        if not datacatastro.empty and infilter:
            if len(datacatastro)>1:
                lista     = datacatastro['predirecc'].tolist()
                listachip = datacatastro['prechip'].tolist()
                index     = 0
                if len(lista)>1 or len(listachip)>1:
                    lista     = ['Todos']+lista
                    listachip = ['Todos']+listachip
                if isinstance(chip_referencia, str):
                    index = listachip.index(chip_referencia)
                with col2:
                    predirecc = st.selectbox('Lista de direcciones',options=lista,index=index)
                    if 'todos' in predirecc.lower(): 
                        chip = None
                    else:
                        chip = datacatastro[datacatastro['predirecc']==predirecc]['prechip'].iloc[0]
            else: chip = datacatastro['prechip'].iloc[0]

        if not datacatastro.empty and not datavigencia.empty: 
            datamerge    = datacatastro[datacatastro['predirecc'].notnull()].drop_duplicates(subset=['prechip'],keep='first')
            datavigencia = datavigencia.merge(datamerge[['prechip','predirecc','preaconst','preaterre']],right_on='prechip',left_on='chip',how='left',validate='m:1')
            datavigencia = datavigencia.sort_values(by='predirecc',ascending=True)
            
        datavigencia_predio = datavigencia.copy()
        if not datavigencia.empty:
            if isinstance(chip, str) and 'todos' not in chip.lower():
                datavigencia_predio = datavigencia[datavigencia['chip']==chip]

        #-------------------------------------------------------------------------#
        # Tabla historial catastral
        #-------------------------------------------------------------------------#
        if not datavigencia_predio.empty:
    
            variables = [x for x in ['link','chip','vigencia','valorAutoavaluo','valorImpuesto','copropiedad','tipoPropietario','tipoDocumento','name','phone','email','predirecc','preaconst','preaterre'] if x in datavigencia_predio]
            datavigencia_predio  = datavigencia_predio[variables]
            
            # Ultimo ano de cada predio
            w                   = datavigencia_predio.groupby(['chip'])['vigencia'].max().reset_index()
            w.columns           = ['chip','maxvigencia']
            datavigencia_predio = datavigencia_predio.merge(w,on='chip',how='left',validate='m:1')
            idd                 = datavigencia_predio['vigencia']==datavigencia_predio['maxvigencia']
            datavigencia_predio = datavigencia_predio[idd]

            html_paso    = ""
            for _,items in datavigencia_predio.iterrows():
                try:    
                    link = items['link'] if 'link' in items and isinstance(items['link'], str) else ""
                    link = f"""
                    <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                       <a href="{link}" target="_blank">
                       <img src="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png" alt="link" width="20" height="20">
                       </a>                    
                    </td>
                    """
                except: link = "<td></td>"
                try:    vigencia = f"<td>{items['vigencia']}</td>" if 'vigencia' in items and (isinstance(items['vigencia'], int) or isinstance(items['vigencia'], float)) else "<td></td>"
                except: vigencia = "<td></td>"
                try:    direccion = f"<td>{items['predirecc']}</td>" if 'predirecc' in items and isinstance(items['predirecc'], str) else "<td></td>"
                except: direccion = "<td></td>"                
                try:    avaluo = f"<td>${items['valorAutoavaluo']:,.0f}</td>" if 'valorAutoavaluo' in items and (isinstance(items['valorAutoavaluo'], int) or isinstance(items['valorAutoavaluo'], float)) else "<td></td>"
                except: avaluo = "<td></td>"
                try:    predial = f"<td>${items['valorImpuesto']:,.0f}</td>" if 'valorImpuesto' in items and (isinstance(items['valorImpuesto'], int) or isinstance(items['valorImpuesto'], float)) else "<td></td>"
                except: predial = "<td></td>"
                try:    areaconstruida = f"<td>{items['preaconst']}</td>" if 'preaconst' in items and (isinstance(items['preaconst'], int) or isinstance(items['preaconst'], float)) else "<td></td>"
                except: areaconstruida = "<td></td>"
                try:    copropiedad = f"<td>{int(items['copropiedad'])}</td>" if 'copropiedad' in items and (isinstance(items['copropiedad'], int) or isinstance(items['copropiedad'], float)) else "<td></td>"
                except: copropiedad = "<td></td>"
                try:    tipopropietario = f"<td>{items['tipoPropietario']}</td>" if 'tipoPropietario' in items and isinstance(items['tipoPropietario'], str) else "<td></td>"
                except: tipopropietario = "<td></td>"
                try:    tipodocumento = f"<td>{items['tipoDocumento']}</td>" if 'tipoDocumento' in items and isinstance(items['tipoDocumento'], str) else "<td></td>"
                except: tipodocumento = "<td></td>"
                try:    name = f"<td>{items['name']}</td>" if 'name' in items and isinstance(items['name'], str) else "<td></td>"
                except: name = "<td></td>"
                try:    phone = f"<td>{items['phone']}</td>" if 'phone' in items and isinstance(items['phone'], str) else "<td></td>"
                except: phone = "<td></td>"
                try:    email = f"<td>{items['email']}</td>" if 'email' in items and isinstance(items['email'], str) else "<td></td>"
                except: email = "<td></td>"
                
                html_paso += f"""
                <tr>
                    {link}
                    {vigencia}
                    {direccion}
                    {avaluo}
                    {predial}
                    {copropiedad}
                    {areaconstruida}
                    {tipopropietario}
                    {tipodocumento}
                    {name}
                    {phone}
                    {email}
                </tr>
                """
            html_paso = f"""
            <thead>
                <tr>
                    <th>Link</th>
                    <th>Vigencia</th>
                    <th>Dirección</th>
                    <th>Avalúo catastral</th>
                    <th>Predial</th>
                    <th>Co-propiedad</th>
                    <th>Área construida</th>
                    <th>Tipo de propietario</th>
                    <th>Tipo de documento</th>
                    <th>Propietario</th>
                    <th>Contacto</th>
                    <th>Email</th>
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
    return html,datavigencia_predio
        
def download_excel(df):
    excel_file = df.to_excel('data_property.xlsx', index=False)
    with open('data_property.xlsx', 'rb') as f:
        data = f.read()
    st.download_button(
        label="Haz clic aquí para descargar",
        data=data,
        file_name='data_property.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
def generar_codigo(x):
    hash_sha256 = hashlib.sha256(x.encode()).hexdigest()
    codigo      = hash_sha256[:12]
    return codigo

def linkPredial(chip,vigencia,idsoporte):
    result = None
    if (isinstance(vigencia, float) or isinstance(vigencia, int)):
        if int(vigencia)==2024:
            filename = generar_codigo(f'{vigencia}{chip}{vigencia}')
            filename = f'{filename.upper()}.pdf'
            result   = f'https://prediales.nyc3.digitaloceanspaces.com/{filename}'
        elif vigencia<2024:
            if isinstance(idsoporte, str):
                result = f"https://oficinavirtual.shd.gov.co/barcode/certificacion?idSoporte={idsoporte}"
    return result

def buildname(nombre1,nombre2,apellido1,apellido2):
    result = ''
    if isinstance(nombre1, str) and nombre1!='':
        result = f"{result} {nombre1}"
    if isinstance(nombre2, str) and nombre2!='':
        result = f"{result} {nombre2}"
    if isinstance(apellido1, str) and apellido1!='':
        result = f"{result} {apellido1}"
    if isinstance(apellido2, str) and apellido2!='':
        result = f"{result} {apellido2}"
    if result!='':
        result = re.sub('\s+',' ',result)
        result = result.strip()
        result = result.title()
    return result

def buildphone(row):
    result = None
    vector = []
    for x in row:
        try: x = str(int(x))
        except: pass
        if isinstance(x, str) and len(x)>=7:
            vector.append(x)
    if vector!=[]:
        vector = list(set(vector))
        result = '|'.join(vector)
    return result

def buildemail(row):
    result = None
    vector = []
    for x in row:
        try: x = str(int(x))
        except: pass
        if isinstance(x, str) and len(x)>=7:
            vector.append(x)
    if vector!=[]:
        vector = [x.lower().strip() for x in vector]
        vector = list(set(vector))
        result = '|'.join(vector)
    return result

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
                background: #A16CFF; 
                position: sticky; 
                top: 0; 
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
