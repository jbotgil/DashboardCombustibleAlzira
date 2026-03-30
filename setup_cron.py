import os
import sys
from crontab import CronTab

def get_python_exe_and_script():
    """Obtiene las rutas absolutas del intérprete y del script."""
    python_exe = sys.executable
    script_path = os.path.abspath("scraper.py")
    return python_exe, script_path

def get_existing_job(cron, script_path):
    """Busca si ya existe una tarea para este script."""
    for job in cron:
        if script_path in job.command:
            return job
    return None

def create_job(cron, python_exe, script_path, schedule):
    """Crea una nueva tarea cron."""
    log_path = os.path.abspath("scraper_cron.log")
    comando = f"{python_exe} {script_path} --una-vez >> {log_path} 2>&1"
    job = cron.new(command=comando, comment='Scraper Combustible Alzira')
    job.setall(schedule)
    return job

def show_menu():
    """Muestra el menú de opciones."""
    print("\n=== Configuración de Cron para Scraper ===")
    print("1. Configurar ejecución automática (cada 24h)")
    print("2. Configurar ejecución cada 12h")
    print("3. Configurar ejecución cada 6h")
    print("4. Configurar ejecución cada hora")
    print("5. Ver tareas programadas")
    print("6. Eliminar tarea programada")
    print("0. Salir")

def get_schedule(option):
    """Devuelve el cron schedule según la opción seleccionada."""
    schedules = {
        '1': '0 8 * * *',      # Cada 24h a las 8:00
        '2': '0 */12 * * *',   # Cada 12h
        '3': '0 */6 * * *',    # Cada 6h
        '4': '0 * * * *',      # Cada hora
    }
    return schedules.get(option)

def get_schedule_description(option):
    """Devuelve una descripción legible del schedule."""
    descriptions = {
        '1': 'diaria a las 8:00',
        '2': 'cada 12 horas',
        '3': 'cada 6 horas',
        '4': 'cada hora',
    }
    return descriptions.get(option, '')

def gestionar_cron():
    python_exe, script_path = get_python_exe_and_script()

    if not os.path.exists(script_path):
        print(f"❌ Error: No se encuentra el archivo {script_path}")
        return

    cron = CronTab(user=True)

    while True:
        show_menu()
        opcion = input("\nSelecciona una opción: ").strip()

        if opcion == '0':
            print("👋 ¡Hasta luego!")
            return

        if opcion == '5':
            # Ver tareas programadas
            print("\n--- Tareas Programadas ---")
            jobs = list(cron)
            if jobs:
                for job in jobs:
                    if script_path in job.command:
                        print(f"  • {job.comment}: {job.schedule}")
            else:
                print("  No hay tareas programadas.")
            continue

        if opcion == '6':
            # Eliminar tarea programada
            job_existente = get_existing_job(cron, script_path)
            if job_existente:
                cron.remove(job_existente)
                cron.write()
                print("🗑️ Tarea eliminada correctamente.")
            else:
                print("ℹ️ No hay ninguna tarea programada para eliminar.")
            continue

        if opcion in ['1', '2', '3', '4']:
            # Configurar nueva frecuencia
            schedule = get_schedule(opcion)
            description = get_schedule_description(opcion)

            job_existente = get_existing_job(cron, script_path)

            if job_existente:
                # Actualizar tarea existente
                job_existente.setall(schedule)
                cron.write()
                print(f"✅ Tarea actualizada: ejecución {description}")
            else:
                # Crear nueva tarea
                job = create_job(cron, python_exe, script_path, schedule)
                cron.write()
                print(f"✅ Tarea creada: ejecución {description}")

            print(f"📝 Log de errores disponible en: {os.path.abspath('scraper_cron.log')}")
            continue

        print("❌ Opción no válida. Por favor, selecciona una opción del menú.")

if __name__ == "__main__":
    gestionar_cron()
