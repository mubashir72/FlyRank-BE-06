# Report API

Invalid input is rejected with a 400 response before a job is queued, while transient failures during valid background work are retried by Inngest.

Use `0 8 * * *` to run every day at 08:00, and `0 22 * * 0` to run every Sunday at 22:00 (using the scheduler's timezone).
