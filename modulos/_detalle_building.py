import streamlit as st
import shapely.wkt as wkt

from functions._principal_getdatareporte import main as getadatareporte
from functions._principal_getpdf import main as _principal_getpdf
from display._principal_reporte_general import main as generar_html


def main(grupo=None):
    
    col1, col2, col3 = st.columns([6, 1,1])
    
    if grupo is not None:
        # Obtener datos
        formato_outputs, data_lote, data_predios, data_transacciones, data_listings, datactl, datalicencias, formato_estadisticas, data_transacciones_historicas, data_construcciones = getadatareporte(grupo)

        try:
            datageometry = data_lote.copy()
            latitud = datageometry['latitud'].iloc[0] if 'latitud' in datageometry and isinstance(datageometry['latitud'].iloc[0], (float,int)) else None
            longitud = datageometry['longitud'].iloc[0] if 'longitud' in datageometry and isinstance(datageometry['longitud'].iloc[0], (float,int)) else None
            polygon = str(wkt.loads(datageometry['wkt'].iloc[0]))
        except:
            latitud = None
            longitud = None
            polygon = None
        
        html_content = generar_html(formato_outputs, data_predios, data_transacciones, data_listings,datactl, datalicencias, formato_estadisticas, data_transacciones_historicas, data_construcciones, latitud, longitud, polygon, grupo=grupo)
        st.components.v1.html(html_content, height=12000, scrolling=True)

        with col2:
            if st.button('Generar PDF'):
                with st.spinner('Procesando PDF...'):
                    
                    # Html version pdf
                    html_content = generar_html(formato_outputs, data_predios, data_transacciones, data_listings,datactl, datalicencias, formato_estadisticas, data_transacciones_historicas, data_construcciones, latitud, longitud, polygon, grupo=grupo, pdfversion=True)
      
                    pdf_bytes = _principal_getpdf(html_content,seccion='_download_pdf_detalle_building')
                    
                    if pdf_bytes:
                        # Ofrecer el PDF para descarga
                        st.download_button(
                            label="Descargar PDF",
                            data=pdf_bytes,
                            file_name="reporte.pdf",
                            mime='application/pdf'
                        )
                    else:
                        st.error("Error al generar el PDF. Por favor intente nuevamente.")
