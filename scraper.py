from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
from datetime import datetime
from urllib.parse import unquote, urlparse, parse_qs
import re

# --- CONFIGURACIÓN DEL USUARIO ---
BUSQUEDAS = input("🔍 Ingresá las marcas a buscar (separadas por coma): ").strip().split(",")
BUSQUEDAS = [b.strip() for b in BUSQUEDAS if b.strip()]

try:
    LIMITE_DIAS = int(input("🗖 ¿Cuántos días como máximo desde su publicación? (ej: 3): ").strip())
except ValueError:
    LIMITE_DIAS = 3

try:
    LIMITE_TOTAL = int(input("⏱ ¿Cuántos autos querés scrapear como máximo? (0 = sin límite): ").strip())
except ValueError:
    LIMITE_TOTAL = 0

FECHA_EXTRACCION = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
ARCHIVO_SALIDA = "autos_filtrados.xlsx"

# --- CONFIGURACIÓN DE NAVEGADOR ---
driver = webdriver.Chrome()
resultados = []
total_scrapeados = 0

# --- FUNCIONES AUXILIARES ---
def scroll_hasta_el_final():
    SCROLL_PAUSA = 1.5
    altura_anterior = 0
    while True:
        altura_actual = driver.execute_script("return document.body.scrollHeight")
        if altura_actual == altura_anterior:
            break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSA)
        altura_anterior = altura_actual

def dias_desde_publicacion(texto):
    texto = texto.lower()
    match = re.search(r"hace (\d+) día", texto)
    if match:
        return int(match.group(1))
    if "hace 1 día" in texto:
        return 1
    if "hace unas horas" in texto:
        return 0
    if "hace más de" in texto or "mes" in texto or "año" in texto:
        return 999  # descartamos
    return 999

# --- SCRAPING DE CADA BÚSQUEDA ---
for termino in BUSQUEDAS:
    print(f"\n🔎 Buscando: {termino}")
    BASE_URL = f"https://listado.mercadolibre.com.uy/{termino.replace(' ', '-')}"
    driver.get(BASE_URL)
    pagina = 1

    while True:
        if LIMITE_TOTAL and total_scrapeados >= LIMITE_TOTAL:
            break

        print(f"🌐 Página {pagina} de '{termino}'...")

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ui-search-layout__item"))
            )
        except:
            print("⛔ No se encontraron productos.")
            break

        scroll_hasta_el_final()
        time.sleep(1)

        contenedores = driver.find_elements(By.CLASS_NAME, "ui-search-layout__item")
        print(f"🔍 Detectados {len(contenedores)} autos")

        links = []
        for contenedor in contenedores:
            try:
                raw_link = contenedor.find_element(By.CLASS_NAME, "poly-component__title").get_attribute("href")
                if "redirect?" in raw_link and "redirect_url=" in raw_link:
                    params = parse_qs(urlparse(raw_link).query)
                    link = unquote(params["redirect_url"][0])
                else:
                    link = raw_link.split('?')[0]
                links.append(link)
            except:
                continue

        for link in links:
            if LIMITE_TOTAL and total_scrapeados >= LIMITE_TOTAL:
                break

            try:
                driver.get(link)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)

                titulo = driver.find_element(By.TAG_NAME, "h1").text
                precio = driver.find_element(By.CLASS_NAME, "andes-money-amount__fraction").text

                try:
                    parrafos = driver.find_elements(By.TAG_NAME, "p")
                    ubicacion = "No disponible"
                    for p in parrafos:
                        clase = p.get_attribute("class")
                        if clase and "ui-pdp-media__title" in clase:
                            texto = p.text.strip()
                            if texto.lower().startswith("el vehículo está en"):
                                ubicacion = texto.replace("El vehículo está en", "").strip()
                                break
                except:
                    ubicacion = "No disponible"

                año = kilometraje = color = motor = combustible = transmision = fecha_publicacion = "No disponible"
                dias_publicado = 999

                try:
                    specs = driver.find_elements(By.CLASS_NAME, "ui-vpp-highlighted-specs__key-value__labels__key-value")
                    for spec in specs:
                        spans = spec.find_elements(By.TAG_NAME, "span")
                        if len(spans) >= 2:
                            campo = spans[0].text.lower().strip().rstrip(":")
                            valor = spans[1].text.strip()
                            if "color" in campo:
                                color = valor
                            elif "motor" in campo:
                                motor = valor
                            elif "combustible" in campo:
                                combustible = valor
                            elif "transmisión" in campo or "transmision" in campo:
                                transmision = valor
                except:
                    pass

                try:
                    detalle = driver.find_element(By.CLASS_NAME, "ui-pdp-subtitle").text
                    if "publicado" in detalle.lower():
                        partes = re.split(r"[\|·]", detalle)
                        for p in partes:
                            p = p.strip()
                            if re.fullmatch(r"\d{4}", p):
                                año = p
                            elif "km" in p.lower():
                                kilometraje = p
                            elif "publicado" in p.lower():
                                fecha_publicacion = p
                                dias_publicado = dias_desde_publicacion(p)
                except:
                    pass

                if dias_publicado <= LIMITE_DIAS:
                    resultados.append({
                        "Búsqueda": termino,
                        "Título": titulo,
                        "Precio": precio,
                        "Ubicación": ubicacion,
                        "Año": año,
                        "Kilometraje": kilometraje,
                        "Color": color,
                        "Motor": motor,
                        "Combustible": combustible,
                        "Transmisión": transmision,
                        "FechaPublicación": fecha_publicacion,
                        "FechaScraping": FECHA_EXTRACCION,
                        "Link": link
                    })
                    total_scrapeados += 1
                    print(f"✅ ({total_scrapeados}) Guardado: {titulo}")
                else:
                    print(f"⏩ Ignorado (más de {LIMITE_DIAS} días): {titulo}")

            except Exception as e:
                print(f"❌ Error en {link}: {e}")
                continue

        try:
            siguiente_li = driver.find_element(By.CSS_SELECTOR, "li.andes-pagination__button--next")
            if "disabled" in siguiente_li.get_attribute("class"):
                break
            siguiente_btn = siguiente_li.find_element(By.TAG_NAME, "a")
            driver.execute_script("arguments[0].scrollIntoView();", siguiente_btn)
            time.sleep(1)
            siguiente_btn.click()
            pagina += 1
            time.sleep(3)
        except:
            break

driver.quit()

# --- EXPORTAR A EXCEL ---
df = pd.DataFrame(resultados)
df.to_excel(ARCHIVO_SALIDA, index=False)
print(f"\n📄 Se guardaron {len(df)} vehículos recientes en '{ARCHIVO_SALIDA}'")
