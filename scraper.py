"""
Scraper de precios de combustible para Alzira.
Extrae datos de la API oficial de Geoportal de Minería (España)
y los almacena en MongoDB.
"""

import json
import time
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Optional
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

from database_config import DatabaseConfig


# Configuración
ALZIRA_COORDINATES = {
    "lat": 39.1540,
    "lon": -0.4350,
    "radio_km": 5  # Radio de búsqueda en km
}

# API oficial del gobierno de España (Ministerio de Industria)
GEOPORTAL_API_URL = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"


class FuelPriceScraper:
    """
    Clase principal para el scraping de precios de combustible.
    """

    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        """
        Inicializa el scraper.

        Args:
            db_config: Instancia de DatabaseConfig (opcional)
        """
        self.db = db_config or DatabaseConfig()
        self.driver = None
        self.estaciones_alzira = []

    def _inicializar_driver(self) -> webdriver.Chrome:
        """
        Inicializa el WebDriver de Chrome con Selenium.

        Returns:
            webdriver.Chrome: Instancia del driver configurado
        """
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver

    def scrape_api_geoportal(self) -> List[Dict]:
        """
        Obtiene los precios de combustible desde la API oficial del Ministerio.

        Returns:
            List[Dict]: Lista de diccionarios con los datos de las estaciones
        """
        print("[SCRAPER] Conectando a la API del Ministerio de Industria...")

        try:
            headers = {
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(GEOPORTAL_API_URL, headers=headers, timeout=30)
            response.raise_for_status()

            # La API puede devolver JSON o XML
            content_type = response.headers.get('Content-Type', '')

            if 'json' in content_type:
                data = response.json()
            else:
                # Intentar parsear como JSON de todos modos
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    # Si no es JSON, intentar con XML
                    data = self._parse_xml(response.text)

            print(f"[SCRAPER] Datos recibidos de la API")
            return self._procesar_datos_api(data)

        except requests.exceptions.RequestException as e:
            print(f"[SCRAPER] Error al conectar con la API: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"[SCRAPER] Error al procesar JSON de la API: {e}")
            return []

    def _parse_xml(self, xml_text: str) -> dict:
        """
        Parsea el XML de la API y lo convierte a diccionario.

        Args:
            xml_text: Texto XML de la respuesta

        Returns:
            dict: Diccionario con los datos parseados
        """
        try:
            root = ET.fromstring(xml_text)
            # La estructura XML de la API devuelve ListaEESSPrecio con EESS
            estaciones = []

            for eess in root.findall('.//EESS'):
                estacion = {}
                for child in eess:
                    estacion[child.tag] = child.text if child.text else ""
                estaciones.append(estacion)

            return {"ListaEESSPrecio": {"EESS": estaciones}}

        except ET.ParseError as e:
            print(f"[SCRAPER] Error al parsear XML: {e}")
            return {}

    def _procesar_datos_api(self, data: dict) -> List[Dict]:
        """
        Procesa los datos recibidos de la API del Ministerio.
        La API devuelve una lista plana de ~12000 estaciones.

        Args:
            data: Datos JSON/XML de la API

        Returns:
            List[Dict]: Lista de registros procesados
        """
        registros = []

        try:
            # La API devuelve ListaEESSPrecio como lista plana de estaciones
            if isinstance(data, dict):
                lista_eess = data.get("ListaEESSPrecio", [])
                if isinstance(lista_eess, list):
                    estaciones = lista_eess
                else:
                    estaciones = []
            elif isinstance(data, list):
                estaciones = data
            else:
                print("[SCRAPER] Formato de datos desconocido")
                return []

            if not estaciones:
                print("[SCRAPER] No se encontraron estaciones en la respuesta")
                return []

            print(f"[SCRAPER] Procesando {len(estaciones)} estaciones del total...")

            for estacion in estaciones:
                try:
                    if not isinstance(estacion, dict):
                        continue

                    # Filtrar estaciones de la zona (Alzira, Alberic, Algemesí, Carcaixent, Xàtiva)
                    cp = str(estacion.get("C.P.", "")).strip()
                    direccion = estacion.get("Dirección", "").lower()
                    municipio = estacion.get("Municipio", "").lower()
                    localidad = estacion.get("Localidad", "").lower()

                    # Verificar si es de la zona
                    municipios_objetivo = ["alzira", "alcira", "alberic", "algemesí", "algemesi", "carcaixent", "xàtiva", "xativa"]
                    es_zona = (
                        any(m in municipio for m in municipios_objetivo) or
                        any(m in localidad for m in municipios_objetivo) or
                        cp in ["46600", "46260", "46680", "46740", "46800"]
                    )

                    if not es_zona:
                        continue

                    registro = self._extraer_datos_estacion(estacion)
                    if registro:
                        registros.append(registro)

                except Exception as e:
                    print(f"[SCRAPER] Error al procesar estación: {e}")
                    continue

            print(f"[SCRAPER] {len(registros)} estaciones de la zona procesadas")
            return registros

        except Exception as e:
            print(f"[SCRAPER] Error en _procesar_datos_api: {e}")
            return []

    def _extraer_datos_estacion(self, estacion: dict) -> Optional[Dict]:
        """
        Extrae los datos relevantes de una estación.
        API del Ministerio devuelve campos con nombres descriptivos:
        - Precio Gasolina 95 E5
        - Precio Gasolina 95 E10
        - Precio Gasoleo A (Diésel B7)
        - Precio Gasoleo B

        Args:
            estacion: Diccionario con los datos de la estación

        Returns:
            Optional[Dict]: Registro procesado o None si hay error
        """
        try:
            nombre = estacion.get("Rótulo", estacion.get("Rotulo", "Desconocido"))
            direccion = estacion.get("Dirección", "Sin dirección")
            municipio = estacion.get("Municipio", "Desconocido")
            cp = estacion.get("C.P.", "Desconocido")
            localidad = estacion.get("Localidad", municipio)

            # Obtener precios - la API usa campos descriptivos
            precio_95 = None
            precio_diesel = None

            # Gasolina 95 E5 o E10
            for key in ["Precio Gasolina 95 E5", "Precio Gasolina 95 E10"]:
                if key in estacion and estacion[key]:
                    try:
                        precio_95 = float(str(estacion[key]).replace(",", "."))
                        break
                    except (ValueError, TypeError):
                        pass

            # Diésel (Gasoleo A = B7, Gasoleo B)
            for key in ["Precio Gasoleo A", "Precio Gasoleo B"]:
                if key in estacion and estacion[key]:
                    try:
                        precio_diesel = float(str(estacion[key]).replace(",", "."))
                        break
                    except (ValueError, TypeError):
                        pass

            # Solo devolver registro si hay al menos un precio
            if precio_95 is None and precio_diesel is None:
                return None

            return {
                "nombre": nombre,
                "direccion": f"{direccion}, {cp} {localidad}",
                "codigo_postal": cp,
                "municipio": municipio,
                "localidad": localidad,
                "gasolina_95": precio_95,
                "diesel_b7": precio_diesel,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        except Exception as e:
            print(f"[SCRAPER] Error al extraer datos de estación: {e}")
            return None

    def scrape_con_selenium(self, url: str = None) -> List[Dict]:
        """
        Método alternativo de scraping usando Selenium.
        Útil si la API no está disponible.

        Args:
            url: URL alternativa para scraping

        Returns:
            List[Dict]: Lista de registros obtenidos
        """
        print("[SCRAPER] Iniciando scraping con Selenium...")
        registros = []

        try:
            self.driver = self._inicializar_driver()

            # URL del geoportal
            target_url = url or "https://geoportal.minco.gob.es/es-es/Paginas/visor.aspx"
            self.driver.get(target_url)

            # Esperar a que cargue el contenido
            time.sleep(5)

            # Buscar el iframe o contenido dinámico
            wait = WebDriverWait(self.driver, 20)

            # Intentar localizar la tabla de precios
            try:
                tabla = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "tabla-precios"))
                )
                html = tabla.get_attribute("outerHTML")
            except:
                html = self.driver.page_source

            # Procesar con BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            registros = self._procesar_html(soup)

        except Exception as e:
            print(f"[SCRAPER] Error en Selenium: {e}")

        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

        return registros

    def _procesar_html(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Procesa el HTML extraído con Selenium.

        Args:
            soup: Objeto BeautifulSoup con el HTML

        Returns:
            List[Dict]: Lista de registros procesados
        """
        registros = []

        # Buscar tablas de precios
        tablas = soup.find_all("table")

        for tabla in tablas:
            filas = tabla.find_all("tr")[1:]  # Saltar cabecera

            for fila in filas:
                columnas = fila.find_all("td")
                if len(columnas) >= 5:
                    try:
                        nombre = columnas[0].text.strip()
                        direccion = columnas[1].text.strip()

                        # Buscar precios de gasolina y diésel
                        for col in columnas[2:]:
                            texto = col.text.strip().lower()
                            if "95" in texto:
                                # Extraer precio
                                pass

                    except Exception as e:
                        continue

        return registros

    def ejecutar_scraping(self) -> int:
        """
        Ejecuta el proceso completo de scraping y guardado en MongoDB.

        Returns:
            int: Número de registros guardados
        """
        print("=" * 60)
        print("[SCRAPER] Iniciando proceso de scraping")
        print(f"[SCRAPER] Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Obtener datos de la API
        registros = self.scrape_api_geoportal()

        # Si no hay datos de la API, intentar con Selenium
        if not registros:
            print("[SCRAPER] API no disponible, intentando con Selenium...")
            registros = self.scrape_con_selenium()

        if not registros:
            print("[SCRAPER] No se pudieron obtener datos")
            return 0

        # Guardar en MongoDB
        print(f"[SCRAPER] Guardando {len(registros)} registros en MongoDB...")
        guardados = self.db.insert_precios_lote(registros)

        print("=" * 60)
        print(f"[SCRAPER] Proceso completado: {guardados} registros guardados")
        print("=" * 60)

        return guardados

    def cerrar(self):
        """Cierra recursos abiertos."""
        if self.driver:
            self.driver.quit()
        if self.db:
            self.db.close()


class ScraperAutomatizado:
    """
    Clase para ejecutar el scraper de forma automatizada con threading.
    """

    def __init__(self, intervalo_horas: float = 1.0):
        """
        Inicializa el scraper automatizado.

        Args:
            intervalo_horas: Intervalo entre ejecuciones en horas
        """
        self.intervalo_horas = intervalo_horas
        self.intervalo_segundos = intervalo_horas * 3600
        self.timer = None
        self.ejecutando = False
        self.scraper = FuelPriceScraper()

    def _ejecutar_y_programar(self):
        """
        Ejecuta el scraping y programa la siguiente ejecución.
        """
        if not self.ejecutando:
            return

        print(f"\n[AUTOMATIZADO] Ejecución programada: {datetime.now()}")

        # Ejecutar scraping
        try:
            self.scraper.ejecutar_scraping()
        except Exception as e:
            print(f"[AUTOMATIZADO] Error en la ejecución: {e}")

        # Programar siguiente ejecución
        if self.ejecutando:
            print(f"[AUTOMATIZADO] Próxima ejecución en {self.intervalo_horas} horas")
            self.timer = threading.Timer(
                self.intervalo_segundos,
                self._ejecutar_y_programar
            )
            self.timer.daemon = True
            self.timer.start()

    def iniciar(self):
        """
        Inicia la ejecución automatizada del scraper.
        """
        print("=" * 60)
        print("[AUTOMATIZADO] Iniciando scraper automatizado")
        print(f"[AUTOMATIZADO] Intervalo: {self.intervalo_horas} horas")
        print(f"[AUTOMATIZADO] Presiona Ctrl+C para detener")
        print("=" * 60)

        self.ejecutando = True

        # Ejecutar inmediatamente la primera vez
        self._ejecutar_y_programar()

        # Mantener el script ejecutándose
        try:
            while self.ejecutando:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[AUTOMATIZADO] Deteniendo scraper...")
            self.detener()

    def detener(self):
        """
        Detiene la ejecución automatizada.
        """
        self.ejecutando = False

        if self.timer:
            self.timer.cancel()
            self.timer = None

        self.scraper.cerrar()
        print("[AUTOMATIZADO] Scraper detenido")


def main():
    """
    Función principal del script.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Scraper de precios de combustible para Alzira"
    )
    parser.add_argument(
        "--intervalo", "-i",
        type=float,
        default=1.0,
        help="Intervalo entre ejecuciones en horas (default: 1.0)"
    )
    parser.add_argument(
        "--una-vez",
        action="store_true",
        help="Ejecutar una sola vez sin automatización"
    )

    args = parser.parse_args()

    if args.una_vez:
        # Ejecución única
        scraper = FuelPriceScraper()
        try:
            scraper.ejecutar_scraping()
        finally:
            scraper.cerrar()
    else:
        # Ejecución automatizada
        automatizado = ScraperAutomatizado(intervalo_horas=args.intervalo)
        automatizado.iniciar()


if __name__ == "__main__":
    main()
