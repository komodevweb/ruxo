# How to Run Monthly Credit Reset Script

This script checks all active subscriptions and resets credits monthly for yearly plans, and when billing periods change for monthly plans.

## Manual Testing (One-Time Run)

**Important:** Always activate the virtual environment first!

### Windows (PowerShell):
```powershell
cd C:\Users\komod\OneDrive\Documents\ruxo\backend
.\venv\Scripts\Activate.ps1
python scripts/reset_monthly_credits.py
```

If you get "execution of scripts is disabled", run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows (Command Prompt):
```cmd
cd C:\Users\komod\OneDrive\Documents\ruxo\backend
venv\Scripts\activate
python scripts/reset_monthly_credits.py
```

### Or Use the Batch File (Easiest):
```cmd
cd C:\Users\komod\OneDrive\Documents\ruxo\backend
scripts\run_credit_reset.bat
```

### Linux/Mac:
```bash
cd /path/to/ruxo/backend
source venv/bin/activate
python scripts/reset_monthly_credits.py
```

## Setting Up Daily Automation

### Option 1: Windows Task Scheduler (Recommended for Windows)

1. **Open Task Scheduler**:
   - Press `Win + R`, type `taskschd.msc`, press Enter

2. **Create Basic Task**:
   - Click "Create Basic Task" in the right panel
   - Name: "Reset Monthly Credits"
   - Description: "Daily credit reset for yearly subscriptions"

3. **Set Trigger**:
   - Trigger: Daily
   - Start time: 2:00 AM (or your preferred time)
   - Recur every: 1 day

4. **Set Action**:
   - Action: Start a program
   - Program/script: `C:\Users\komod\OneDrive\Documents\ruxo\backend\venv\Scripts\python.exe`
   - Add arguments: `scripts/reset_monthly_credits.py`
   - Start in: `C:\Users\komod\OneDrive\Documents\ruxo\backend`

5. **Set Conditions** (Optional):
   - Uncheck "Start the task only if the computer is on AC power"
   - Check "Wake the computer to run this task" (if needed)

6. **Save** and test by right-clicking the task → "Run"

### Option 2: Windows Task Scheduler (Advanced - with environment variables)

If you need environment variables (like `.env` file), create a batch file:

**Create `backend/scripts/run_credit_reset.bat`**:
```batch
@echo off
cd /d C:\Users\komod\OneDrive\Documents\ruxo\backend
call venv\Scripts\activate.bat
python scripts/reset_monthly_credits.py
```

Then in Task Scheduler:
- Program/script: `C:\Users\komod\OneDrive\Documents\ruxo\backend\scripts\run_credit_reset.bat`
- Start in: `C:\Users\komod\OneDrive\Documents\ruxo\backend`

### Option 3: Linux/Mac Cron Job

1. **Open crontab**:
   ```bash
   crontab -e
   ```

2. **Add this line** (runs daily at 2:00 AM):
   ```cron
   0 2 * * * cd /path/to/ruxo/backend && /path/to/venv/bin/python scripts/reset_monthly_credits.py >> /var/log/credit_reset.log 2>&1
   ```

   Replace paths with your actual paths:
   ```cron
   0 2 * * * cd /home/user/ruxo/backend && /home/user/ruxo/backend/venv/bin/python scripts/reset_monthly_credits.py >> /var/log/credit_reset.log 2>&1
   ```

3. **Save and exit** (in vim: press `Esc`, type `:wq`, press Enter)

### Option 4: Using Python's `schedule` Library (Development/Testing)

Create a simple scheduler script:

**`backend/scripts/scheduler.py`**:
```python
import schedule
import time
import subprocess
import sys
from pathlib import Path

def run_credit_reset():
    """Run the credit reset script."""
    backend_dir = Path(__file__).parent.parent)
    script_path = backend_dir / "scripts" / "reset_monthly_credits.py"
    python_exe = sys.executable
    
    result = subprocess.run([python_exe, str(script_path)], 
                          cwd=str(backend_dir),
                          capture_output=True,
                          text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Errors: {result.stderr}")

# Schedule to run daily at 2:00 AM
schedule.every().day.at("02:00").do(run_credit_reset)

print("Credit reset scheduler started. Will run daily at 2:00 AM.")
print("Press Ctrl+C to stop.")

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
```

Run it:
```bash
cd backend
python scripts/scheduler.py
```

## Verification

After running the script, you should see output like:
```
Checking for subscriptions that need credit resets...
Reset credits for subscription <id> (user <user_id>)
Reset credits for 1 subscription(s)
Done!
```

## Troubleshooting

1. **"Module not found" error**:
   - Make sure you're in the `backend` directory
   - Make sure the virtual environment is activated
   - Make sure all dependencies are installed: `pip install -r requirements.txt`

2. **"Database connection error"**:
   - Check that your `.env` file has correct `DATABASE_URL`
   - Make sure the database is running

3. **"No subscriptions found"**:
   - This is normal if there are no active subscriptions
   - Check your database to verify subscriptions exist

4. **Windows Task Scheduler not running**:
   - Check Task Scheduler → Task Scheduler Library → find your task → check "Last Run Result"
   - Make sure the user account has permission to run the task
   - Check Windows Event Viewer for errors

## Logging

The script prints to console. For production, you may want to redirect output to a log file:

**Windows Task Scheduler**:
- Add to "Add arguments": `>> C:\logs\credit_reset.log 2>&1`

**Linux/Mac Cron**:
- Already included in the cron example above

## Best Practices

1. **Run during low-traffic hours** (e.g., 2:00 AM)
2. **Monitor logs** regularly to ensure it's running
3. **Test manually** before setting up automation
4. **Set up alerts** if the script fails (optional)

