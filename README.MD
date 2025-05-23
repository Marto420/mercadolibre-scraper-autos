Este script permite scrapear información detallada de vehículos publicados en MercadoLibre Uruguay, ingresando a cada anuncio individual. 
Genera un .xlsx para importarlo en un excel con todos los vehiculos.

## ¿Que extrae?
- Título
- Precio
- Ubicación 
- Año
- Kilometraje
- Color
- Motor
- Combustible
- Transmisión
- Fecha de publicación
- Fecha del scraping
- link

## Como usarlo

requisitos previos:
- tener phyton 3 instalado
- decargar el chromedriver que coincida con tu version de chrome, y colocarlo en la carpeta donde se ubica el scraper

## Paso a paso
- paso 1: clonar el repo
- paso 2: en la terminal, descargar las dependencias necesarias con pip install -r requirements.txt
- paso 3: ejecutar el script con: python scraper.py

como resultado te dara un .xlsx para que puedas importarlo en tu excel
