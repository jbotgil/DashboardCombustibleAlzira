# ⛽ Monitor de Precios de Combustible

Sistema de monitorización de precios de combustible (Gasolina 95 y Diésel B7) para la Comunidad Valenciana.

## 📋 Descripción del Proyecto

Proyecto educativo para la asignatura de **Sistemas de Big Data** (UD3 - Web Scraping) que implementa un ecosistema completo:

- **Web Scraping** automático de la API oficial del [Geoportal de Minería](https://geoportal.minco.gob.es)
- **Almacenamiento** en MongoDB para mantener histórico de precios
- **Dashboard interactivo** con Streamlit para visualización de datos
- **Automatización** mediante threading y Task Scheduler (Windows) / cron (Linux)

## 🏗️ Arquitectura

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│  API Geoportal  │────▶│   Scraper    │────▶│  MongoDB    │────▶│  Dashboard  │
│  (Ministerio)   │     │  (Python)    │     │  (Docker)   │     │ (Streamlit) │
└─────────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   Timer      │
                        │ (Threading)  │
                        └──────────────┘
```

## 📦 Requisitos Previos

### 1. Python 3.12+

```bash
python --version
```

### 2. MongoDB y Mongo Express (Docker Compose)

El proyecto incluye un archivo `compose.yaml` que levanta la base de datos MongoDB junto con Mongo Express (una interfaz de administración vía web).

Para iniciar los servicios, ejecuta:

```bash
docker compose up -d
```

Verificar que los contenedores están corriendo:

```bash
docker compose ps
```

Puedes acceder a la interfaz web de Mongo Express en `http://localhost:8081` utilizando las credenciales:
- **Usuario:** `adminweb`
- **Contraseña:** `webPass123`

### 3. Google Chrome / Chromium

Necesario para el scraping con Selenium:

```bash
# Verificar Chrome
google-chrome --version

# O verificar Chromium
chromium --version
```

## 🚀 Instalación

### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/jbotgil/DashboardCombustibleAlzira.git
cd DashboardCombustibleAlzira
```

### Paso 2: Crear y activar entorno virtual

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

### Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con las credenciales de MongoDB:

```env
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USER=admin
MONGO_PASS=miPassword123
```

## 📁 Estructura del Proyecto

```
WebScrapingUD3/
├── .venv/                  # Entorno virtual
├── .env.example            # Ejemplo de variables de entorno
├── .gitignore              # Archivos a ignorar en Git
├── database_config.py      # Configuración de MongoDB
├── scraper.py              # Script de web scraping
├── dashboard.py            # Dashboard de Streamlit
├── requirements.txt        # Dependencias de Python
└── README.md               # Documentación
```

## 🔧 Uso

### Ejecutar el Scraper

```bash
source .venv/bin/activate

# Ejecución única
python scraper.py --una-vez

# Ejecutar cada 1 hora (default)
python scraper.py

# Ejecutar cada 30 minutos
python scraper.py --intervalo 0.5

# Ejecutar cada 6 horas
python scraper.py --intervalo 6
```

### Ejecutar el Dashboard

```bash
source .venv/bin/activate
streamlit run dashboard.py
```

El dashboard se abrirá en: `http://localhost:8501`

## 📊 Características del Dashboard

El dashboard incluye las siguientes visualizaciones:

1. **Métricas principales**
   - Precio medio de Gasolina 95 y Diésel B7
   - Gasolinera más barata
   - Número de gasolineras monitorizadas

2. **Gráfico de barras comparativo**
   - Comparación de precios entre gasolineras

3. **Gráfico de dispersión**
   - Relación entre precios de gasolina y diésel

4. **Mapa de calor**
   - Visualización tipo matriz con códigos de color

5. **Ranking de precios**
   - Tablas ordenadas con gradiente de color

6. **Filtros interactivos**
   - Por municipio
   - Por tipo de combustible
   - Mostrar solo los más baratos

## 🪟 Automatización

### Windows Task Scheduler

Crear tarea programada:

```cmd
schtasks /Create /TN "ScraperCombustible" /TR "python.exe C:\ruta\scraper.py --una-vez" /SC HOURLY /MO 1 /RU "SYSTEM" /F
```

### Linux / macOS (cron)

El proyecto incluye un script interactivo para configurar, modificar o eliminar automáticamente la tarea en cron. Esto te permite programar la ejecución diaria de una forma muy sencilla.

Para utilizarlo, simplemente ejecuta:

```bash
source .venv/bin/activate
python setup_cron.py
```

El asistente te guiará y toda la salida de la ejecución programada se registrará en el archivo `scraper_cron.log`.

**Configuración manual (Alternativa):**

Si prefieres editar el `crontab` tú mismo:

```bash
crontab -e
```

Añade esta línea para ejecutar el script cada hora (ajusta las rutas):

```cron
0 * * * * cd /ruta/al/proyecto && /ruta/al/.venv/bin/python scraper.py --una-vez
```

## 🐛 Solución de Problemas

### MongoDB no conecta

```bash
# Verificar estado
docker compose ps

# Reiniciar contenedores
docker compose restart

# Ver logs
docker compose logs mongo
```

### Error con Selenium/ChromeDriver

```bash
# Reinstalar webdriver-manager
pip uninstall webdriver-manager
pip install webdriver-manager
```

### No hay datos en el dashboard

1. Ejecutar el scraper manualmente:
   ```bash
   python scraper.py --una-vez
   ```

2. Verificar datos en MongoDB (o usa Mongo Express en http://localhost:8081):
   ```bash
   docker exec -it mongo_db mongosh -u admin -p miPassword123
   > use combustible_alzira
   > db.precios_combustible.countDocuments()
   ```

## 📄 Licencia

Este proyecto es de uso educativo para la asignatura de Sistemas de Big Data.

## 👨‍💻 Autor

Desarrollado para la UD3 de Web Scraping - Sistemas de Big Data

## 📝 Notas

- Los datos se obtienen de la API oficial del Ministerio para la Transición Ecológica
- El scraper siempre añade nuevos registros para mantener el histórico
- Para producción, se recomienda usar cron o Task Scheduler en lugar de threading
