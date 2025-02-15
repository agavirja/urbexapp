import streamlit as st

st.set_page_config(layout='wide',page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

# streamlit run D:\Dropbox\Empresa\Urbex\_APP_heroku\Home.py
# https://streamlit.io/
# pipreqs --encoding utf-8 "D:\Dropbox\Empresa\Urbex\_APP_heroku"

#------------#
# Powersheel #

# Archivos donde esta la palabra "urbextestapp\.streamlit\.app" o "urbextestapp\.streamlit\.app"
# Get-ChildItem -Path D:\Dropbox\Empresa\Urbex\_APP_heroku -Recurse -Filter *.py | ForEach-Object { if (Get-Content $_.FullName | Select-String -Pattern 'localhost:8501' -Quiet) { $_.FullName } }

# Reemplazar "localhost:8501" por "localhost:8501" o al reves en los archivos donde esta la palabra
# Get-ChildItem -Path D:\Dropbox\Empresa\Urbex\_APP_heroku -Recurse -Filter *.py | ForEach-Object {(Get-Content $_.FullName) | ForEach-Object {$_ -replace 'localhost:8501', 'localhost:8501'} | Set-Content $_.FullName}
# Get-ChildItem -Path 'C:\Users\LENOVO T14\Documents\GitHub\urbexapp' -Recurse -Filter *.py | ForEach-Object {(Get-Content $_.FullName) | ForEach-Object {$_ -replace 'localhost:8501', 'www.urbex.com.co'} | Set-Content $_.FullName}

html = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Página de Información de Propiedades</title>
  <style>
  
    /* General Styles */
    body, html {
      margin: 0;
      padding: 0;
      font-family: Arial, sans-serif;
      scroll-behavior: smooth;
    }
    h2 {
      color: #333;
      text-align: center;
      margin-bottom: 20px;
    }

    /* Section 1 Styles */
    .hero-section {
      position: relative;
      background-image: url('https://iconsapp.nyc3.digitaloceanspaces.com/_landing_page_img/msv39.jpg');
      background-size: cover;  /* Cubre todo el contenedor manteniendo la proporción */
      background-position: center center;  /* Centra la imagen */
      background-repeat: no-repeat;  /* Evita que la imagen se repita */
      height: 12vh;  /* Altura responsiva */
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      text-align: center;
      padding: 0 20px;
    }

    .hero-section::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.4);
      z-index: 1;
    }

    .hero-content {
      position: relative;
      z-index: 2;
      background: rgba(0, 0, 0, 0.8);
      padding: 20px;
      border-radius: 20px;
      max-width: 600px;
      height:300px;
    }

    .hero-content h1 {
      font-size: 2em;
      margin-bottom: 20px;
    }

    .cta-button {
      background-color: #a738cd;
      color: white;
      padding: 10px 20px;
      border: none;
      border-radius: 5px;
      font-size: 1em;
      cursor: pointer;
      text-decoration: none;
      transition: background 0.3s;
    }
    .cta-button:hover {
      background-color: #8c2ca3;
    }

    /* New Intermediate Section Styles */
    .ideal-section {
      background-color: #f0f0f0;
      padding: 50px 20px;
    }
    .ideal-header {
      text-align: center;
      font-size: 1.8em;
      margin-bottom: 30px;
      color: #333;
    }
    .ideal-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      max-width: 1200px;
      margin: 0 auto;
    }
    .ideal-item {
      background-color: white;
      border-radius: 10px;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      overflow: hidden;
      text-align: center;
      padding: 20px;
    }
    .ideal-item img {
      width: 60%;
      height: auto;
      object-fit: cover;
      filter: grayscale(100%);
      border-radius: 10px;
      margin: 15px 0;
    }
    .ideal-item h3 {
      color: #a738cd;
      font-size: 1.5em;
      margin: 15px 0;
    }
    .ideal-item p {
      padding: 0 15px 15px;
      text-align: left;
      font-size: 1em;
      color: #666;
      line-height: 1.5;
    }
    .ideal-item p span {
      display: block;
      font-weight: bold;
      color: #333;
    }

    /* Section 2 Styles */
    .contact-section {
      padding: 50px 20px;
      background-color: #f5f5f5;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .contact-form {
      max-width: 600px;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 15px;
    }
    .contact-form input, .contact-form textarea {
      width: 100%;
      padding: 10px;
      border: 1px solid #ccc;
      border-radius: 5px;
      font-size: 1em;
    }
    .contact-form textarea {
      resize: vertical;
      height: 100px;
    }
    .submit-button {
      background-color: #a738cd;
      color: white;
      padding: 10px 20px;
      border: none;
      border-radius: 5px;
      font-size: 1em;
      cursor: pointer;
      transition: background 0.3s;
    }
    .submit-button:hover {
      background-color: #8c2ca3;
    }

    /* Section 2: Información que puedes encontrar */
    .info-section {
      padding: 50px 20px;
      background-color: #f9f9f9;
      text-align: center;
    }
    .info-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      max-width: 1200px;
      margin: 0 auto;
    }
    .info-item {
      padding: 20px;
      background-color: white;
      border-radius: 8px;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .info-icon {
      font-size: 50px;
      color: #a738cd;
    }
    .info-title {
      font-size: 1.2em;
      margin: 15px 0 10px;
    }
    .info-description {
      color: #555;
    }


    /* Section Logos: */
    .logos-container {
      overflow: hidden;
      padding: 60px 0;
      background: white;
      position: relative;
      width: 100%;
    }
    
    .logos-track {
      display: flex;
      width: calc(250px * 38); /* Aumenta el ancho para incluir todos los logos */
      animation: scroll 20s linear infinite; /* Ralentiza la animación */
    }
    
    .logo {
      flex: 0 0 250px; /* Aumenta el ancho de cada logo */
      height: 100px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 20px;
    }
    
    .logo img {
      max-width: 180px; /* Aumenta el tamaño máximo de los logos */
      max-height: 100px;
      width: auto;
      height: auto;
      object-fit: contain;
      filter: grayscale(100%) contrast(1.2);
      opacity: 0.8;
      transition: all 0.3s ease;
    }
    
    .logo img:hover {
      filter: grayscale(0%) contrast(1);
      opacity: 1;
    }
    
    @keyframes scroll {
      0% {
        transform: translateX(0);
      }
      100% {
        transform: translateX(calc(-250px * 19)); /* Ajusta para un desplazamiento suave */
      }
    }
    
    .logos-container:hover .logos-track {
      animation-play-state: paused;
    }


    /* Section Equipo: */
    .team-section {
        padding: 4rem 2rem;
        background-color: #f8f9fa;
    }
    
    /* Grid de 2x2 */
    .team-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 3rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Estilos para cada miembro del equipo */
    .team-member {
        text-align: center;
        padding: 1rem;
    }
    
    /* Contenedor de la imagen circular */
    .image-container {
        width: 200px;
        height: 200px;
        margin: 0 auto 1.5rem;
        border-radius: 50%;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Asegura que la imagen cubra perfectamente el contenedor circular */
    .image-container img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    /* Estilos para el nombre */
    .member-name {
        font-size: 1.5rem;
        color: #333;
        margin-bottom: 0.5rem;
    }
    
    /* Estilos para el título */
    .member-title {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 1rem;
    }
    
    /* Estilos para la descripción */
    .member-description {
        font-size: 0.9rem;
        color: #777;
        line-height: 1.6;
    }


    /* Responsive Design */
    @media (max-width: 768px) {
      .team-grid {
        grid-template-columns: 1fr;
        gap: 2rem;
      }
    
      .image-container {
        width: 150px;
        height: 150px;
      }
    
      .member-name {
        font-size: 1.3rem;
      }
    
      .member-title {
        font-size: 1rem;
      }
        
      .hero-content h1 {
        font-size: 1.5em;
      }
      .contact-section {
        padding: 30px 10px;
      }
      .ideal-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>

  <!-- (Titulo) -->
  <section class="hero-section">
    <div class="hero-content">
      <h1 style="margin-bottom:80px;">Accede a toda la información de cualquier propiedad o lote de forma fácil y rápida</h1>
      <a href="#contact-section" class="cta-button">Conoce más</a>
    </div>
  </section>

  <!-- (Info) -->
  <section class="info-section">
    <h2>¿Qué información puedes encontrar en Urbex?</h2>
    <div class="info-grid">
      <div class="info-item">
        <div class="info-icon">📊</div>
        <div class="info-title">Precios de cierre</div>
        <div class="info-description">Contamos con todos los precios de cierre de las propiedades para que tengas un precio de referencia más ajustado</div>
      </div>
      <div class="info-item">
        <div class="info-icon">📈</div>
        <div class="info-title">Últimas transacciones</div>
        <div class="info-description">Cuáles son las últimas transacciones o anotaciones de una propiedad</div>
      </div>
      <div class="info-item">
        <div class="info-icon">🏠</div>
        <div class="info-title">Avalúos catastrales y prediales</div>
        <div class="info-description">Histórico de los avalúos catastrales e impuesto prediales</div>
      </div> 
      <div class="info-item">
        <div class="info-icon">📞</div>
        <div class="info-title">Datos de contacto de propietarios</div>
        <div class="info-description">Acceso a información de contacto de quienes son los propietarios de cada predio</div>
      </div>
      <div class="info-item">
        <div class="info-icon">💰</div>
        <div class="info-title">Dinámicas de precios de oferta en venta y renta</div>
        <div class="info-description">Análisis de cómo se han comportado los precios en venta y renta en el sector</div>
      </div>
      <div class="info-item">
        <div class="info-icon">🌍</div>
        <div class="info-title">Lotes, licencias de construcción y normativa urbana</div>
        <div class="info-description">Análisis de prefactibilidad de desarrollo inmobiliario en cada lote de acuerdo a la normativa urbana vigente</div>
      </div>
    </div>
  </section>

    <!-- Logos -->
    <div class="logos-container">
      <h2 style="margin-bottom:50px;">Empresas que utilizan Urbex</h2>
    
      <div class="logos-track">
        <!-- Logos originales -->
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-kiruna.png" alt="Kiruna">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-mendebal.png" alt="Mendebal">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-coandes.png" alt="Coandes">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-blackhorse.png" alt="Blackhorse">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-terpel.png" alt="Terpel">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-cbre.png" alt="CBRE">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-colliers.png" alt="Colliers">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-paladin.png" alt="Paladin">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-logan.png" alt="Logan">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-diagonal2.png" alt="Diagonal2">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-cumbrera.png" alt="Cumbrera">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-pads.png" alt="Pads">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-inmobiliariabogota.png" alt="InmobiliariaBogota">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-grupomacana.png" alt="GrupoMacana">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-abg.png" alt="abg">
        </div>
        <div class="logo">
          <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-rv.png" alt="rv">
        </div>
      </div>
    </div>


  <!-- (Ideal para..) -->
  <section class="ideal-section">
    <div class="ideal-header">Ideal para ...</div>
    <div class="ideal-grid">
      <div class="ideal-item">
        <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_landing_page_img/msv29.jpg" alt="Equipos comerciales" style="width: 50%; height: auto;">
        <h3 class="highlight-text">Equipos comerciales</h3>
        <ul>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Generar leads de propietarios segmentados y georreferenciados</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Engorde de leads con información de propiedades y vehículos</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Seguimiento de precios en el mercado secundario de los proyectos de las constructoras</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Estudios de mercado a la medida</li>
        </ul>
      </div>
      <div class="ideal-item">
        <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_landing_page_img/msv33.jpg" alt="Expansion" style="width: 50%; height: auto;">
        <h3>Equipos de expansión</h3>
        <ul>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Acceder a cualquier tipo de activo inmobiliario, aún cuando no está listado en el mercado</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Anlálisis de georreferenciación de la competencia</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Acceso a datos de contacto de propietarios de los locales de interés</li>
        </ul>
      </div>
      <div class="ideal-item">
        <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_landing_page_img/msv31.jpg" alt="Estructuración" style="width: 50%; height: auto;">
        <h3>Equipos de estructuración</h3>
        <ul>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Algoritmo para búsqueda activa de lotes</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Consolidación de lotes</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Acceso a datos de quienes son los propietarios de cada lote</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Análisis de prefactibilidad según la normativa urbana vigente y potencial de desarrollo del lote</li>
        </ul>
      </div>
      <div class="ideal-item">
        <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_landing_page_img/msv36.jpg" alt="Brokeraje" style="width: 50%; height: auto;">
        <h3>Brokeraje</h3>
        <ul>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Due diligence de cualquier activo inmobiliario en tiempo real</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Potencializar la captación de activos para venta o arriendo</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Estudio de mercado y análisis de precios de cierre, oferta y avalúos catastrales</li>
            <li style="text-align: left; margin: 5px 0; word-wrap: break-word; list-style-position: inside; padding-left: 20px; text-indent: -20px;">Generación de reportes</li>
        </ul>
      </div>
    </div>
  </section>



  <!-- (Equipo) -->
<section class="team-section">
    <div class="team-grid">
        <!-- Miembro del equipo 1 -->
        <div class="team-member">
            <div class="image-container">
                <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_founders_workers_img/alejandrogaviriaimg.jpg" alt="alejandrogaviria">
            </div>
            <h3 class="member-name">Alejandro Gaviria</h3>
            <p class="member-title">Co-fundador</p>
            <p class="member-description">Ex-Habi Chief of Data | Ex-Buydepa Country Manager y Chief of Data </p>
        </div>

        <!-- Miembro del equipo 2 -->
        <div class="team-member">
            <div class="image-container">
                <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_founders_workers_img/diegorodriguezimg.jpg" alt="diegorodriguez">
            </div>
            <h3 class="member-name">Diego Rodriguez</h3>
            <p class="member-title">Co-fundador</p>
            <p class="member-description">Ex-socio Corredores Asociados | Ex-socio Correval | Co-fundador Bosk Capital  </p>
        </div>

        <!-- Miembro del equipo 3 -->
        <div class="team-member">
            <div class="image-container">
                <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_founders_workers_img/germanrojasimg.jpg" alt="germanrojas">
            </div>
            <h3 class="member-name">German Rojas</h3>
            <p class="member-title">Co-fundador</p>
            <p class="member-description">Co-Fundador y Managing Partner en Kiruna Capital Partner | Ex gerente general de Terranum</p>
        </div>

        <!-- Miembro del equipo 4 -->
        <div class="team-member">
            <div class="image-container">
                <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_founders_workers_img/felipepachecoimg.jpg" alt="felipepacheco">
            </div>
            <h3 class="member-name">Felipe Pacheco</h3>
            <p class="member-title">Co-fundador</p>
            <p class="member-description">Socio en Kiruna Capital Partner | Ex-Brigard & Urrutia Abogados </p>
        </div>
    </div>
</section>


  <!-- (Contact Form) -->
  <section id="contact-section" class="contact-section">
    <h2>Contáctanos</h2>
    <form class="contact-form">
      <input type="text" name="name" placeholder="Nombre" required>
      <input type="email" name="email" placeholder="Correo Electrónico" required>
      <input type="text" name="phone" placeholder="Teléfono" required>
      <textarea name="message" placeholder="Mensaje" required></textarea>
      <button type="submit" class="submit-button">Enviar</button>
    </form>
  </section>

<script>
document.addEventListener('DOMContentLoaded', function() {
    var ctaButton = document.querySelector('.cta-button');
    ctaButton.addEventListener('click', function(e) {
        e.preventDefault();
        var contactSection = document.getElementById('contact-section');
        contactSection.scrollIntoView({ behavior: 'smooth' });
    });
});
</script>
</body>
</html>
"""
#st.markdown(html,unsafe_allow_html=True)
st.components.v1.html(html, height=5000, scrolling=True)



#<div class="logo">
#  <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-maya.png" alt="Maya">
#</div>
#<div class="logo">
#  <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-uraki.png" alt="Uraki">
#</div>
#<div class="logo">
#  <img src="https://iconsapp.nyc3.digitaloceanspaces.com/_clientes_logos/canva-logo-jll.png" alt="jll">
#</div>
