# How to View Live Backend Logs

## Real-Time Live Logs (Like Terminal)

### Option 1: Follow Live Logs (Recommended)
```bash
sudo journalctl -u ruxo-backend -f
```
- `-f` = follow (like `tail -f`)
- Shows new logs as they appear in real-time
- Press `Ctrl+C` to exit

### Option 2: Follow with Timestamps
```bash
sudo journalctl -u ruxo-backend -f --no-pager
```
- Same as above but ensures no pager

### Option 3: Follow Last 100 Lines Then Continue
```bash
sudo journalctl -u ruxo-backend -n 100 -f
```
- Shows last 100 lines first, then continues with new logs

## View Recent Logs

### Last 50 Lines
```bash
sudo journalctl -u ruxo-backend -n 50 --no-pager
```

### Last 100 Lines
```bash
sudo journalctl -u ruxo-backend -n 100 --no-pager
```

### Last 200 Lines
```bash
sudo journalctl -u ruxo-backend -n 200 --no-pager
```

## Filter Logs

### Search for Specific Terms
```bash
# Search for "error"
sudo journalctl -u ruxo-backend -f | grep -i error

# Search for "webhook"
sudo journalctl -u ruxo-backend -f | grep -i webhook

# Search for "redis"
sudo journalctl -u ruxo-backend -f | grep -i redis

# Search for "stripe"
sudo journalctl -u ruxo-backend -f | grep -i stripe
```

### View Logs Since a Specific Time
```bash
# Last 10 minutes
sudo journalctl -u ruxo-backend --since "10 minutes ago" --no-pager

# Last hour
sudo journalctl -u ruxo-backend --since "1 hour ago" --no-pager

# Today
sudo journalctl -u ruxo-backend --since today --no-pager

# Specific date
sudo journalctl -u ruxo-backend --since "2025-11-23 00:00:00" --no-pager
```

### View Logs Between Times
```bash
sudo journalctl -u ruxo-backend --since "2025-11-23 10:00:00" --until "2025-11-23 11:00:00" --no-pager
```

## View by Log Level

### Only Errors
```bash
sudo journalctl -u ruxo-backend -p err -f
```

### Errors and Warnings
```bash
sudo journalctl -u ruxo-backend -p warning -f
```

## Most Useful Commands

### 1. Live Logs (Most Common)
```bash
sudo journalctl -u ruxo-backend -f
```

### 2. Recent Logs with Errors Highlighted
```bash
sudo journalctl -u ruxo-backend -n 100 --no-pager | grep -E "ERROR|error|Error|WARNING|warning"
```

### 3. Live Logs Filtered for Important Events
```bash
sudo journalctl -u ruxo-backend -f | grep -E "ERROR|WARNING|webhook|subscription|payment"
```

## Quick Reference

| Command | What It Does |
|--------|-------------|
| `sudo journalctl -u ruxo-backend -f` | **Live logs (follow mode)** |
| `sudo journalctl -u ruxo-backend -n 50` | Last 50 lines |
| `sudo journalctl -u ruxo-backend --since "10 minutes ago"` | Logs from last 10 minutes |
| `sudo journalctl -u ruxo-backend -p err` | Only error level logs |
| `sudo journalctl -u ruxo-backend -f \| grep error` | Live logs filtered for errors |

## Tips

1. **Use `-f` for live monitoring** - This is like watching logs in a terminal
2. **Press `Ctrl+C` to stop** following logs
3. **Use `--no-pager`** to avoid pagination (useful for scripts)
4. **Combine with `grep`** to filter for specific terms
5. **Use `-n` to limit** initial output before following

## Example: Monitor Webhook Events Live

```bash
sudo journalctl -u ruxo-backend -f | grep -i webhook
```

This will show you webhook events in real-time as they happen!

## Example: Monitor All API Requests

```bash
sudo journalctl -u ruxo-backend -f | grep -E "GET|POST|PUT|DELETE"
```

## Check Backend Status

```bash
# Check if backend is running
sudo systemctl status ruxo-backend

# View recent startup logs
sudo journalctl -u ruxo-backend --since "5 minutes ago" | head -30
```

