import os
import sys
from crontab import CronTab

def gestionar_cron():
    # Obtener la ruta absoluta del intérprete de python y del script
    # Esto asegura que el cron sepa exactamente qué ejecutar
    python_exe = sys.executable
    script_path = os.path.abspath("scraper.py")
    
    if not os.path.exists(script_path):
        print(f"❌ Error: No se encuentra el archivo {script_path}")
        return

    cron = CronTab(user=True)
    # Buscamos si ya existe una tarea para este script específico
    job_existente = None
    for job in cron:
        if script_path in job.command:
            job_existente = job
            break

    print("--- Gestor de Programación (Crontab) ---")

    if job_existente:
        # Extraer hora y minuto actuales del cron
        hora = job_existente.hour.render()
        minuto = job_existente.minute.render()
        print(f"✅ Ya tienes una tarea programada: Todos los días a las {hora}:{minuto.zfill(2)}")
        
        opcion = input("¿Qué deseas hacer? [C]ambiar hora, [D]esactivar/Eliminar, [S]alir: ").lower()
        
        if opcion == 'd':
            cron.remove(job_existente)
            cron.write()
            print("🗑️ Tarea eliminada correctamente.")
            return
        elif opcion == 's':
            return
        # Si es 'c', sigue el flujo de abajo
    else:
        print("ℹ️ No hay ninguna programación activa para scraper.py")
        opcion = input("¿Deseas programar una nueva tarea diaria? (s/n): ").lower()
        if opcion != 's':
            return

    # Configurar nueva hora
    try:
        print("\nConfigura la ejecución diaria:")
        nueva_hora = int(input("Introduce la hora (0-23): "))
        nuevo_minuto = int(input("Introduce el minuto (0-59): "))

        if not (0 <= nueva_hora <= 23 and 0 <= nuevo_minuto <= 59):
            raise ValueError("Hora o minuto fuera de rango.")

        # Si ya existía, la actualizamos. Si no, la creamos.
        if job_existente:
            job = job_existente
        else:
            # Importante: Redirigimos la salida a un log para que puedas ver si falla
            log_path = os.path.abspath("scraper_cron.log")
            comando = f"{python_exe} {script_path} >> {log_path} 2>&1"
            job = cron.new(command=comando, comment='Scraper Combustible Alzira')

        job.setall(f"{nuevo_minuto} {nueva_hora} * * *")
        cron.write()
        
        print(f"🚀 Programado con éxito: Todos los días a las {nueva_hora}:{str(nuevo_minuto).zfill(2)}")
        print(f"Log de errores disponible en: {os.path.abspath('scraper_cron.log')}")

    except ValueError as e:
        print(f"❌ Entrada no válida: {e}")

if __name__ == "__main__":
    gestionar_cron()