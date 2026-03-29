# Role: Senior Python & Data Engineer
# Task: End-to-End Web Scraping, Storage, and Dashboarding (Fuel Prices)

Actúa como un ingeniero de datos experto. El objetivo es construir un ecosistema completo en Python para monitorizar los precios del combustible (Gasolina 95 y Diésel) en la localidad de **Alzira**.

## 1. Contexto del Ecosistema
El proyecto debe integrarse en un entorno de Big Data local que ya cuenta con:
- **Base de Datos:** MongoDB (corriendo en Docker).
- **Localización:** Alzira, Valencia.
- **Visualización:** Panel interactivo con Streamlit.

## 2. Requisitos del Script de Web Scraping (`scraper.py`)
- **Extracción:** Usa `Selenium` o `BeautifulSoup` para obtener datos en tiempo real de estaciones de servicio en Alzira. 
- **Datos a capturar:** Nombre de la gasolinera, dirección completa, precio de Gasolina 95 (E5) y Diésel (B7).
- **Transformación:** Limpia los datos (convierte precios a float) y añade un timestamp (ISO 8601).
- **Carga:** Inserta los datos en la colección `precios_combustible` de MongoDB. No sobrescribas, añade nuevos registros para mantener un histórico.

## 3. Automatización (Basado en documentación técnica)
Implementa dos estrategias de ejecución recurrente:
- **Estrategia Interna (Threading):** Usa la clase `Timer` de `threading` para que el script se mantenga residente y ejecute la función de scraping cada X horas (basado en el PDF "Ejecución planificada de código en python").
- **Estrategia Externa (Windows Task Scheduler):** Proporciona las instrucciones exactas para crear una tarea en Windows que ejecute el script diariamente (basado en el PDF "Automatizar Scripts Python en Windows").

## 4. Visualización con Streamlit (`dashboard.py`)
Crea una aplicación web moderna que:
- Se conecte a MongoDB y extraiga el histórico de precios.
- **Filtros:** Permitir filtrar por gasolinera o por tipo de combustible.
- **Gráficos:** - Comparativa de precios actuales entre gasolineras (Gráfico de barras).
    - Evolución histórica de precios en Alzira (Gráfico de líneas).
- **Métricas:** Mostrar la gasolinera más barata del día mediante `st.metric`.

## 5. Formato de Salida (Markdown Detallado)
Genera el código en bloques separados y bien comentados:
1. `requirements.txt` (con las librerías necesarias).
2. `database_config.py` (clase de conexión a MongoDB).
3. `scraper.py` (lógica de extracción y automatización).
4. `dashboard.py` (interfaz de Streamlit).
5. Un `README.md` detallado con instrucciones de despliegue y configuración del Programador de Tareas de Windows.