import logging
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()
reports: dict[str, dict[str, object]] = {}

inngest_client = inngest.Inngest(
    app_id="report-api",
    logger=logging.getLogger("uvicorn"),
)


class ReportRequest(BaseModel):
    topic: str | None = None


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("sleep", timedelta(seconds=5))
    return "Hello from the background!"


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,
)
async def make_report(ctx: inngest.Context) -> dict[str, str]:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await ctx.step.sleep("do-the-slow-work", timedelta(seconds=8))

    async def build_report() -> dict[str, str]:
        if topic == "fail":
            raise RuntimeError("The report oven is broken!")

        result = {
            "topic": topic,
            "summary": f"Report about {topic}",
        }
        outbox = Path("outbox")
        outbox.mkdir(exist_ok=True)
        (outbox / f"{report_id}.txt").write_text(
            f"Report about {topic}\n{result['summary']}\n",
            encoding="utf-8",
        )
        reports[report_id].update(status="done", result=result)
        return result

    result = await ctx.step.run("build-report", build_report)
    reports[report_id].update(status="done", result=result)
    return result


@inngest_client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def heartbeat(ctx: inngest.Context) -> None:
    counts = {
        status: sum(report["status"] == status for report in reports.values())
        for status in ("pending", "done", "failed")
    }
    ctx.logger.info(
        "Report heartbeat: pending=%d done=%d failed=%d",
        counts["pending"],
        counts["done"],
        counts["failed"],
    )


inngest.fast_api.serve(app, inngest_client, [say_hello, make_report, heartbeat])


@app.post("/reports", status_code=status.HTTP_202_ACCEPTED)
async def create_report(request: ReportRequest) -> dict[str, str]:
    if request.topic is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic is required",
        )

    report_id = str(uuid4())
    reports[report_id] = {
        "id": report_id,
        "topic": request.topic,
        "status": "pending",
    }
    await inngest_client.send(
        inngest.Event(
            name="report/requested",
            data={"id": report_id, "topic": request.topic},
        )
    )
    return {"id": report_id, "status": "pending"}


@app.get("/reports")
def list_reports() -> list[dict[str, object]]:
    return list(reports.values())


@app.get("/reports/{report_id}")
def get_report(report_id: str) -> dict[str, object]:
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return report


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
