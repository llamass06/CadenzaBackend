import asyncio
from app.config import MAX_PROCESOS

class DemucsTaskManager:
    """Clase para encapsular el estado y los locks del procesamiento de audio."""
    def __init__(self, max_procesos: int):
        self.semaforo = asyncio.Semaphore(max_procesos)
        self.lock = asyncio.Lock()
        self.tareas_activas = 0
        self.tareas_en_proceso = 0
        self.tareas_en_espera = 0
        self.tareas_separacion = {}

    async def registrar_tarea(self, task_id: str):
        self.tareas_separacion[task_id] = {"status": "waiting"}
        async with self.lock:
            self.tareas_activas += 1
            self.tareas_en_espera += 1

    async def iniciar_proceso(self, task_id: str):
        self.tareas_separacion[task_id] = {"status": "processing"}
        async with self.lock:
            self.tareas_en_espera = max(0, self.tareas_en_espera - 1)
            self.tareas_en_proceso += 1

    async def finalizar_proceso(self):
        async with self.lock:
            self.tareas_en_proceso = max(0, self.tareas_en_proceso - 1)

    async def finalizar_tarea(self):
        async with self.lock:
            self.tareas_activas = max(0, self.tareas_activas - 1)



    def actualizar_estado(self, task_id: str, estado: str, result: dict = None, error: str = None):
        datos = {"status": estado}
        if result:
            datos["result"] = result
        if error:
            datos["error"] = error
        self.tareas_separacion[task_id] = datos

    def obtener_tarea(self, task_id: str):
        return self.tareas_separacion.get(task_id)

    def estado_cola(self):
        return {
            "tareas_activas": self.tareas_activas,
            "tareas_en_proceso": self.tareas_en_proceso,
            "tareas_esperando": self.tareas_en_espera,
            "saturado": self.tareas_en_espera >= 1
        }

# Instancia global del gestor para usar en toda la aplicación
task_manager = DemucsTaskManager(MAX_PROCESOS)
