import asyncio

from src.infrastructure.task_registry import TaskRegistry


@TaskRegistry.register("exemplo-com-pausa")
class ExemploTask:
    def __init__(self, runner=None):
        self._runner = runner

    @staticmethod
    def get_schema():
        return [
            {"name": "mensagem", "label": "Mensagem", "type": "string"},
            {"name": "espera_segundos", "label": "Espera (segundos)", "type": "number"},
        ]

    async def execute(self, params: dict) -> dict:
        msg = params.get("mensagem", "Sem mensagem")
        delay = float(params.get("espera_segundos", 3))

        if self._runner:
            await self._runner.report_step("preparando")
        await asyncio.sleep(1)

        if self._runner:
            await self._runner.report_step(f"esperando {delay}s")
        # Pausa pelo tempo definido sem travar o event loop
        # O checkpoint garante que pause/cancel funcionem
        for i in range(int(delay)):
            await asyncio.sleep(1)
            if self._runner:
                await self._runner.checkpoint(f"aguardando... {i+1}s")

        if self._runner:
            await self._runner.report_step(f"mensagem: {msg}")
        print(f"Mensagem: {msg}")

        if self._runner:
            await self._runner.report_step("concluido")

        return {"mensagem": msg, "delay": delay}
