from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
from datetime import datetime
from urllib.parse import unquote, urlparse, parse_qs
import re

# Inputs
BUSQUEDA = input("🔍 ¿Qué querés buscar? (ej: bmw): ").strip()
try:
    LIMITE = int(input("⏱ ¿Cuántos autos querés scrapear? (0 = sin límite): ").strip())
except ValueError:
    LIMITE = 0

BASE_URL = f"https://listado.mercadolibre.com.uy/{BUSQUEDA.replace(' ', '-')}"
ARCHIVO = f"autos_{BUSQUEDA}_detallado.xlsx"
FECHA_EXTRACCION = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

driver = webdriver.Chrome()
driver.get(BASE_URL)

resultados = []
pagina = 1
total_scrapeados = 0

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

while True:
    print(f"🌐 Procesando página {pagina}...")

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
    print(f"🔍 Detectados {len(contenedores)} autos en página {pagina}")

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
        if LIMITE and total_scrapeados >= LIMITE:
            break

        try:
            driver.get(link)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)

            titulo = driver.find_element(By.TAG_NAME, "h1").text
            precio = driver.find_element(By.CLASS_NAME, "andes-money-amount__fraction").text

            # ✅ UBICACIÓN real desde el <p> correcto
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
            except:
                pass

            resultados.append({
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
            print(f"✅ ({total_scrapeados}) {titulo}")
        except Exception as e:
            print(f"❌ Falló en {link}: {e}")
            continue

    if LIMITE and total_scrapeados >= LIMITE:
        print("⏹ Se alcanzó el límite.")
        break

    try:
        siguiente_li = driver.find_element(By.CSS_SELECTOR, "li.andes-pagination__button--next")
        if "disabled" in siguiente_li.get_attribute("class"):
            print("🏁 No hay más páginas.")
            break
        siguiente_btn = siguiente_li.find_element(By.TAG_NAME, "a")
        driver.execute_script("arguments[0].scrollIntoView();", siguiente_btn)
        time.sleep(1)
        siguiente_btn.click()
        pagina += 1
        time.sleep(3)
    except:
        print("🏁 Fin del paginado.")
        break

driver.quit()

# 📦 Guardar en Excel
df = pd.DataFrame(resultados)
df.to_excel(ARCHIVO, index=False)
print(f"\n📄 Se guardaron {len(df)} autos en '{ARCHIVO}'")
