import streamlit as st
import requests
import re
import random
from bs4 import BeautifulSoup

from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.html_to_pdf_job import HTMLtoPDFJob
from adobe.pdfservices.operation.pdfjobs.params.html_to_pdf.html_to_pdf_params import HTMLtoPDFParams
from adobe.pdfservices.operation.pdfjobs.result.html_to_pdf_result import HTMLtoPDFResult

from data.tracking import savesearch

def main(html_content,seccion=None):
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
        'token': None,
    }
    
    for key, value in formato.items():
        if key not in st.session_state:
            st.session_state[key] = value
            
    # CSS URLs
    css_urls = [
        "https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_bootstrap.min.css",
        "https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_styles.css"
    ]
    # Procesar HTML con CSS embebido
    processed_html = process_html_with_css(html_content, css_urls)
    
    pdf_bytes = html_to_pdf(processed_html)
    if st.session_state.token is not None:
        seccion = '_download_pdf' if seccion is None else seccion
        savesearch(st.session_state.token, None, seccion, None)

    return pdf_bytes

@st.cache_resource(show_spinner=False)
def html_to_pdf(html_content):
    try:
        # Configurar credenciales
        pdf_client_id_1     = st.secrets["pdf_client_id_1"]
        pdf_client_secret_1 = st.secrets["pdf_client_secret_1"]
        pdf_email_1         = st.secrets["pdf_email_1"]
        
        pdf_client_id_2     = st.secrets["pdf_client_id_2"]
        pdf_client_secret_2 = st.secrets["pdf_client_secret_2"]
        pdf_email_2         = st.secrets["pdf_email_2"]
                
        credentials_list = [
            {"client_id": pdf_client_id_1, "client_secret":pdf_client_secret_1, "email":pdf_email_1},
            {"client_id": pdf_client_id_2, "client_secret":pdf_client_secret_2, "email":pdf_email_2},
        ]
        
        # Seleccionar un set de credenciales aleatoriamente
        selected_credentials = random.choice(credentials_list)
        
        # Configurar las credenciales seleccionadas
        credentials = ServicePrincipalCredentials(
            client_id=selected_credentials["client_id"],
            client_secret=selected_credentials["client_secret"]
        )
        
        # Inicializar servicio
        pdf_services = PDFServices(credentials=credentials)
        
        # Convertir el HTML string a bytes
        html_bytes = html_content.encode('utf-8')
        
        # Subir el HTML
        input_asset = pdf_services.upload(
            input_stream=html_bytes,
            mime_type=PDFServicesMediaType.HTML
        )
        
        # Configurar y ejecutar la conversión
        params = HTMLtoPDFParams(include_header_footer=False)
        job = HTMLtoPDFJob(input_asset=input_asset, html_to_pdf_params=params)
        location = pdf_services.submit(job)
        
        # Obtener el resultado
        response = pdf_services.get_job_result(location, HTMLtoPDFResult)
        result_asset = response.get_result().get_asset()
        pdf_content = pdf_services.get_content(result_asset)
        
        return pdf_content.get_input_stream()
        
    except Exception as e:
        st.error(f"Error en la conversión a PDF: {e}")
        return None
    
def download_css_content(urls):
    css_content = ""
    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            css_content += f"/* CSS from {url} */\n" + response.text + "\n"
        except requests.RequestException as e:
            st.error(f"Error downloading CSS from {url}: {e}")
    return css_content

def remove_media_queries(css_content):
    return re.sub(r'@media[^{]*\{[^}]*\}', '', css_content, flags=re.DOTALL)

def process_html_with_css(html_content, css_urls):

    # Crear objeto BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Descargar y procesar CSS
    css_combined = download_css_content(css_urls)
    cleaned_css = remove_media_queries(css_combined)
    
    # Eliminar los links a CSS externos
    for link in soup.find_all("link", href=True):
        if link["href"] in css_urls:
            link.decompose()
    
    # Añadir el CSS limpio
    style_tag = soup.new_tag("style")
    style_tag.string = cleaned_css
    
    if soup.head:
        soup.head.append(style_tag)
    else:
        head_tag = soup.new_tag("head")
        head_tag.append(style_tag)
        soup.html.insert(0, head_tag)
    
    return str(soup)
