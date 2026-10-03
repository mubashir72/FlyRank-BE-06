import logging
from datetime import timedelta

import inngest
import inngest.fast_api
from fastapi import FastAPI

app = FastAPI()
inngest_client = inngest.Inngest(
    app_id="report-api",
    logger=logging.getLogger("uvicorn"),
)


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("sleep", timedelta(seconds=5))
    return "Hello from the background!"


inngest.fast_api.serve(app, inngest_client, [say_hello])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
