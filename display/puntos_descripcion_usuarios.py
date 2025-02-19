def pasosApp(numeral, titulo, descripcion):
    style = """
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f9f9f9;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .step-container {
            background-color: #fff;
            border: 2px solid #ccc;
            border-radius: 10px;
            padding: 15px 20px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            width: 100%;  /* Ocupa todo el ancho disponible */
            max-width: none;  /* Se elimina la restricción de ancho máximo */
            margin-bottom: 20px; /* Margin inferior para separar del resto */
            font-size: 14px;
        }
        .header {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }
        .circle {
            background-color: #A16CFF;
            color: #fff;
            width: 25px;
            height: 25px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin-right: 10px;
            font-size: 1em;
        }
        .circle_small {
            background-color: #A16CFF;
            color: #fff;
            width: 15px;
            height: 15px;
            border-radius: 50%;
            display: inline-flex;
            justify-content: center;
            align-items: center;
            margin-right: 10px;
            font-size: 1em;
            vertical-align: middle;
        }
        .titulo {
            color: #B241FA;
            font-size: 10px;  /* Tamaño de fuente reducido para el título */
            margin: 0;
            font-weight: bold;
        }
        .descripcion {
            color: #555;
            font-size: 8px;  /* Tamaño de fuente reducido para la descripción */
            margin: 0;
        }
    </style>
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        {style}
    </head>
    <body>
        <div class="step-container">
            <div class="header">
                <div class="circle">{numeral}</div>
                <p class="titulo" >{titulo}</p>
            </div>
            <p class="descripcion" >{descripcion}</p>
        </div>
    </body>
    </html>
    """
    return html


def procesoCliente(proceso_actual):
    if proceso_actual < 1:
        proceso_actual = 1
    if proceso_actual > 5:
        proceso_actual = 5

    style = """
    <style>
        .process-container {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            margin: 20px 0;
        }
        .circle {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.9em;
            margin: 0 5px;
        }
        /* Estilo para bolas completadas */
        .filled {
            background-color: #A16CFF;
            color: #fff;
            border: none;
        }
        /* Estilo para bolas pendientes */
        .empty {
            background-color: #fff;
            color: #000;
            border: 2px solid #A16CFF;
        }
        .line {
            height: 2px;
            flex-grow: 1;
            background-color: #A16CFF;
        }
    </style>
    """
    # Generamos el HTML de las 5 bolas conectadas por líneas
    circles_html = ""
    for i in range(1, 6):
        # Asignar clase según el estado del paso
        clase = "filled" if i <= proceso_actual else "empty"
        # Bola
        circles_html += f'<div class="circle {clase}">{i}</div>'
        # Si no es la última, agregar la línea
        if i < 5:
            circles_html += '<div class="line"></div>'

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {style}
    </head>
    <body>
        <div class="process-container">
            {circles_html}
        </div>
    </body>
    </html>
    """
    return html
