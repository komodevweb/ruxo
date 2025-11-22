# Background Scheduler Setup

The application now uses **APScheduler** to automatically handle monthly credit resets for yearly subscriptions. This is much better than external cron jobs because:

## ✅ Advantages

1. **No External Setup Required**: Runs automatically when the FastAPI app starts
2. **Centralized**: All scheduling logic is in the codebase
3. **Easy to Test**: Can be tested in development
4. **Works Everywhere**: Dev, staging, and production - no OS-specific setup
5. **Automatic**: Starts/stops with the application
6. **Reliable**: If the app is running, the scheduler is running

## How It Works

The scheduler runs **daily at 2:00 AM** and checks all active subscriptions:
- **Yearly plans**: Resets credits every month (if a month has passed since last reset)
- **Monthly plans**: Resets when billing period changes (handled by Stripe webhooks)

## Installation

1. **Install the dependency** (already added to `requirements.txt`):
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **That's it!** The scheduler starts automatically when you run the FastAPI app.

## Verification

When you start the backend server, you should see in the logs:
```
INFO: Starting background scheduler...
INFO: Scheduler configured: Credit reset task scheduled daily at 2:00 AM
INFO: Background scheduler started successfully
```

## Manual Testing

You can manually trigger the credit reset task by calling the function directly:

```python
from app.services.scheduler_service import reset_monthly_credits_task
import asyncio

asyncio.run(reset_monthly_credits_task())
```

Or create a test endpoint (for development only):

```python
# In a router (development only!)
@app.post("/admin/test-credit-reset")
async def test_credit_reset():
    from app.services.scheduler_service import reset_monthly_credits_task
    await reset_monthly_credits_task()
    return {"status": "done"}
```

## Configuration

The scheduler runs daily at **2:00 AM** by default. To change this, edit `backend/app/services/scheduler_service.py`:

```python
scheduler.add_job(
    reset_monthly_credits_task,
    trigger=CronTrigger(hour=2, minute=0),  # Change time here
    ...
)
```

## Monitoring

The scheduler logs all activities:
- When the task starts
- Which subscriptions were reset
- Any errors that occur

Check your application logs to monitor the scheduler's activity.

## Troubleshooting

1. **Scheduler not starting**: Check that APScheduler is installed: `pip install apscheduler==3.10.4`
2. **No logs**: Check your log level in `.env`: `LOG_LEVEL=INFO`
3. **Credits not resetting**: Check the logs for errors, verify subscriptions exist and are active

## Migration from Cron/Task Scheduler

If you were using the external script (`reset_monthly_credits.py`), you can now:
- **Remove the cron/task scheduler setup** - it's no longer needed
- **Keep the script** for manual testing if needed
- The scheduler handles everything automatically

## Production Deployment

The scheduler works automatically in production:
- **Single instance**: If you have multiple app instances, each will run the scheduler
- **No conflicts**: The scheduler uses `max_instances=1` to prevent duplicate runs
- **Coalescing**: If multiple runs are missed, it only runs once when the app starts

For production with multiple instances, consider:
- Using a distributed lock (Redis, etc.) if you want only one instance to run the task
- Or let each instance run it (the task is idempotent, so it's safe)


