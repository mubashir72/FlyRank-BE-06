# Background Jobs API

A small FastAPI service demonstrating event-triggered background work with Inngest. Report requests are accepted immediately, processed by a durable background function, and exposed through a polling endpoint. A separate cron function logs a report-status heartbeat every minute.

## Run locally

Install Python dependencies once:

```powershell
python -m pip install -r requirements.txt
```

Start the Inngest Dev Server in terminal 1:

```powershell
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
```

Start the API in terminal 2 (use the Dev Server's address if it selected a different port):

```powershell
$env:INNGEST_DEV = "http://localhost:8288"; python -m uvicorn main:app --reload --port 8000
```

Open the Inngest dashboard at <http://localhost:8288>. If port 8288 is already occupied, the Dev Server selects another port; set `INNGEST_DEV` to that address before starting the API.

## Endpoints

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/health` | Returns `{"status":"ok"}`. |
| `POST` | `/reports` | Accepts `{"topic":"cats"}`, queues a report, and immediately returns HTTP 202 with its ID and `pending` status. A missing topic returns HTTP 400 without queuing a job. |
| `GET` | `/reports/{id}` | Returns the saved report (`pending` while processing, then `done` with its result); unknown IDs return HTTP 404. |
| `GET`, `POST`, `PUT` | `/api/inngest` | Inngest function discovery and execution endpoint. |

Reports are kept in memory, so they are cleared when the API process restarts.

## Inngest functions

| Function | Trigger | Behavior |
|---|---|---|
| `say-hello` | `test/hello` | Sleeps for five seconds and returns `Hello from the background!`. |
| `make-report` | `report/requested` | Sleeps for eight seconds, then builds and stores a report. It retries twice; topic `fail` intentionally throws on every attempt to demonstrate final failure. |
| `heartbeat` | `* * * * *` | Every minute, logs the counts of pending, done, and failed reports. |

## Example report polling proof

```text
POST /reports
HTTP 202
{"id":"57476115-b00c-441a-b455-a0c79413b30a","status":"pending"}

GET /reports/57476115-b00c-441a-b455-a0c79413b30a  (first poll)
{"id":"57476115-b00c-441a-b455-a0c79413b30a","topic":"cats","status":"pending"}

GET /reports/57476115-b00c-441a-b455-a0c79413b30a  (about 10 seconds later)
{"id":"57476115-b00c-441a-b455-a0c79413b30a","topic":"cats","status":"done","result":{"summary":"Report about cats","topic":"cats"}}
```

## Retry and validation lesson

Invalid input is rejected with a 400 response before a job is queued, while transient failures during valid background work are retried by Inngest.

## Cron schedule examples

Use `0 8 * * *` to run every day at 08:00, and `0 22 * * 0` to run every Sunday at 22:00 (using the scheduler's timezone).

## Dashboard proof

The screenshot shows the failed `make-report` run after its initial attempt and two retries, successful report processing, and minute-spaced heartbeat runs.

![Inngest dashboard showing background report and cron runs](screenshots/dashboard.png)
