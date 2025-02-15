def pasosApp(texto,numero):
    style = """
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f9f9f9;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
    
        .step-container {
            background-color: #fff;
            border: 2px solid #ccc;
            border-radius: 10px;
            padding: 10px 20px; /* Reducir el padding */
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
            height: 30px;
        }
    
        .circle {
            background-color: #A16CFF;
            color: #fff;
            width: 15px;
            height: 15px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin-right: 10px;
            font-size: 0.8em; /* Reducir el tamaño de la fuente */
        }
    
        .step {
            color: #B241FA;
            font-size: 0.8em; /* Reducir el tamaño de la fuente */
            margin: 0;
        }
    </style>
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
        {style}
    </head>
    <body>
        <div class="step-container" style="margin-bottom: 20px;">
            <div class="circle">{numero}</div>
            <p class="step">{texto}</p>
        </div>
    </body>
    </html>
    """
    return html
