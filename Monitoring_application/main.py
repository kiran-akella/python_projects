from fastapi import FastAPI, Depends, Request, BackgroundTasks
from fastapi.security import HTTPBasic
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psutil
import sqlite3
from datetime import datetime, timedelta
from typing import List
import os
import time
import threading
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import io
from matplotlib import pyplot as plt
import uvicorn

from code.db_utils import store_resource_usage, should_store_new_entry, get_history
from code.alert_utils import send_alert_email
from code.auth_utils import authenticate


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

security = HTTPBasic()

DB_PATH = 'resource_data.db'
CREDENTIALS_FILE = 'config/creds.json'
EMAILS_FILE = 'config/emails.json'
SMTP_FILE = 'config/smtp.json'

last_io_check = {'time': time.time(), 'read': 0, 'write': 0}
last_cpu_check = {'time': time.time(), 'value': 0}

# Add these constants near other configurations at the top
DATA_RETENTION_DAYS = 7  # Keep data for 1 week only
CLEANUP_INTERVAL_HOURS = 24  # Run cleanup once a day

# --- Status Endpoint ---
class StatusResponse(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    uptime: str

@app.get("/status", response_model=StatusResponse)
def get_status(user: str = Depends(authenticate), background_tasks: BackgroundTasks = None):
    global last_cpu_check
    current_time = time.time()
    
    # Only get new CPU reading if more than 1 second has passed
    if current_time - last_cpu_check['time'] >= 1:
        cpu = psutil.cpu_percent(interval=None)  # Non-blocking call
        last_cpu_check.update({'time': current_time, 'value': cpu})
    else:
        cpu = last_cpu_check['value']
    
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    uptime_seconds = int(time.time() - psutil.boot_time())
    uptime_str = time.strftime('%H:%M:%S', time.gmtime(uptime_seconds))
    
    if should_store_new_entry():
        if background_tasks:
            background_tasks.add_task(store_resource_usage, cpu, mem, disk)
        else:
            store_resource_usage(cpu, mem, disk)
            
    return {
        "cpu_percent": cpu,
        "memory_percent": mem,
        "disk_percent": disk,
        "uptime": uptime_str
    }

# --- Analytics Endpoints ---
class StatsResponse(BaseModel):
    avg_cpu_percent: float | None
    avg_memory_percent: float | None
    avg_disk_percent: float | None

@app.get("/stats", response_model=StatsResponse)
def get_stats(user: str = Depends(authenticate)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT AVG(cpu_percent), AVG(memory_percent), AVG(disk_percent) FROM resource_usage''')
    avg_cpu, avg_mem, avg_disk = c.fetchone()
    conn.close()
    return {
        "avg_cpu_percent": avg_cpu,
        "avg_memory_percent": avg_mem,
        "avg_disk_percent": avg_disk
    }

class DiskIOResponse(BaseModel):
    read_speed: float
    write_speed: float
    total_speed: float

@app.get("/diskio", response_model=DiskIOResponse)
def get_diskio(user: str = Depends(authenticate)):
    global last_io_check
    current_time = time.time()
    io = psutil.disk_io_counters()
    
    # Calculate delta
    time_delta = current_time - last_io_check['time']
    read_delta = io.read_bytes - last_io_check['read']
    write_delta = io.write_bytes - last_io_check['write']
    
    # Update last check
    last_io_check = {
        'time': current_time,
        'read': io.read_bytes,
        'write': io.write_bytes
    }
    
    # Convert to MB/s
    if time_delta > 0:
        read_speed = (read_delta / 1024 / 1024) / time_delta  # MB/s
        write_speed = (write_delta / 1024 / 1024) / time_delta  # MB/s
    else:
        read_speed = write_speed = 0
        
    return {
        "read_speed": round(read_speed, 2),
        "write_speed": round(write_speed, 2),
        "total_speed": round(read_speed + write_speed, 2)
    }

templates = Jinja2Templates(directory="frontend")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: str = Depends(authenticate)):
    try:
        # Get latest status
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        # System uptime and last reboot with error handling
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = int(time.time() - psutil.boot_time())
        uptime_str = time.strftime('%H:%M:%S', time.gmtime(uptime_seconds))
        last_reboot_date = boot_time.strftime("%d-%B %Y")
        last_reboot_time = boot_time.strftime("%H:%M:%S")

        # Get history with error handling
        history_data = get_history(1)  # Get last day's data for dashboard
        
        # Get averages with default values
        avg_cpu, avg_mem, avg_disk = 0, 0, 0
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''SELECT AVG(cpu_percent), AVG(memory_percent), AVG(disk_percent) FROM resource_usage''')
            averages = c.fetchone()
            if averages and None not in averages:
                avg_cpu, avg_mem, avg_disk = averages
            conn.close()
        except Exception as e:
            print(f"Error fetching averages: {e}")
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "cpu_percent": cpu,
            "memory_percent": mem,
            "disk_percent": disk,
            "uptime": uptime_str,
            "last_reboot_date": last_reboot_date,
            "last_reboot_time": last_reboot_time,
            "history": history_data or [],
            "avg_cpu_percent": round(avg_cpu or 0, 2),
            "avg_memory_percent": round(avg_mem or 0, 2),
            "avg_disk_percent": round(avg_disk or 0, 2),
            "username": user
        })
    except Exception as e:
        print(f"Dashboard error: {e}")
        # Return a basic error response
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "error": "Failed to load dashboard data",
            "username": user
        })

# --- Email alerting logic ---
# --- Load emails and SMTP config ---
def load_emails():
    if os.path.exists(EMAILS_FILE):
        with open(EMAILS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('emails', [])
    return []

def load_smtp():
    if os.path.exists(SMTP_FILE):
        with open(SMTP_FILE, 'r') as f:
            return json.load(f)
    return None

# --- Generate dashboard snapshot as an image (simple text+icons) ---
def generate_dashboard_snapshot(cpu, mem, disk):
    # Create a simple bar chart snapshot
    fig, ax = plt.subplots(figsize=(4,2))
    categories = ['CPU', 'Memory', 'Disk']
    values = [cpu, mem, disk]
    colors = ['#ff6666', '#66b3ff', '#99ff99']
    bars = ax.bar(categories, values, color=colors)
    ax.set_ylim(0, 100)
    ax.set_ylabel('% Usage')
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, val + 2, f'{val:.1f}%', ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf.read()

# --- Improved send_alert_email with HTML and inline snapshot ---
def send_alert_email(subject, body, cpu=None, mem=None, disk=None):
    smtp_conf = load_smtp()
    if not smtp_conf:
        print('[ALERT] SMTP config missing!')
        return
    recipients = load_emails()
    if not recipients:
        print('[ALERT] No recipients in emails.json!')
        return
    msg = MIMEMultipart()
    msg['From'] = smtp_conf.get('from_email')
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject
    # Add graphical icons and HTML formatting
    html = f"""
    <html><body>
    <h2 style='color:#d9534f;'>⚠️ Resource Monitor Alert</h2>
    <p>{body.replace(chr(10), '<br>')}</p>
    <ul style='font-size:1.1em;'>
      <li>🖥️ <b>CPU:</b> {cpu:.2f}%</li>
      <li>💾 <b>Memory:</b> {mem:.2f}%</li>
      <li>🗄️ <b>Disk:</b> {disk:.2f}%</li>
    </ul>
    <p><b>Snapshot at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</b></p>
    <img src='cid:snapshot' style='max-width:350px;border:1px solid #ccc;border-radius:8px;'>
    </body></html>
    """
    msg.attach(MIMEText(html, 'html'))
    # Attach snapshot image
    if cpu is not None and mem is not None and disk is not None:
        img_data = generate_dashboard_snapshot(cpu, mem, disk)
        image = MIMEImage(img_data, name='snapshot.png')
        image.add_header('Content-ID', '<snapshot>')
        msg.attach(image)
    try:
        server = smtplib.SMTP(smtp_conf['host'], smtp_conf['port'])
        if smtp_conf.get('use_tls', False):
            server.starttls()
        server.login(smtp_conf['username'], smtp_conf['password'])
        server.sendmail(smtp_conf['from_email'], recipients, msg.as_string())
        server.quit()
        print('[ALERT] Email sent!')
    except Exception as e:
        print(f'[ALERT] Failed to send email: {e}')

# --- Alert logic ---
alert_state = {'cpu': False, 'mem': False, 'disk': False}

def check_and_alert(cpu, mem, disk):
    threshold = 80
    alerts = []
    if cpu >= threshold and not alert_state['cpu']:
        alerts.append(f'CPU usage is high: {cpu:.2f}%')
        alert_state['cpu'] = True
    elif cpu < threshold:
        alert_state['cpu'] = False
    if mem >= threshold and not alert_state['mem']:
        alerts.append(f'Memory usage is high: {mem:.2f}%')
        alert_state['mem'] = True
    elif mem < threshold:
        alert_state['mem'] = False
    if disk >= threshold and not alert_state['disk']:
        alerts.append(f'Disk usage is high: {disk:.2f}%')
        alert_state['disk'] = True
    elif disk < threshold:
        alert_state['disk'] = False
    if alerts:
        send_alert_email(
            subject=f"⚠️ Resource Alert: {', '.join([a.split()[0] for a in alerts])} High Usage!",
            body='\n'.join(alerts),
            cpu=cpu, mem=mem, disk=disk
        )

# --- Background resource collector thread ---
def background_resource_collector():
    last_cleanup = datetime.now()
    while True:
        try:
            # Existing resource collection code
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            store_resource_usage(cpu, mem, disk)
            check_and_alert(cpu, mem, disk)
            
            # Add cleanup check
            if (datetime.now() - last_cleanup).total_seconds() >= CLEANUP_INTERVAL_HOURS * 3600:
                cleanup_old_data()
                last_cleanup = datetime.now()
                
        except Exception as e:
            print(f"[ResourceCollector] Error: {e}")
        time.sleep(4)  # 1s for cpu_percent + 4s sleep = ~5s interval

# --- Cleanup old data ---
def cleanup_old_data():
    """Remove data older than DATA_RETENTION_DAYS days"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=DATA_RETENTION_DAYS)).isoformat()
        c.execute('DELETE FROM resource_usage WHERE timestamp < ?', (cutoff_date,))
        conn.commit()
        conn.close()
        print(f"[Cleanup] Removed data older than {DATA_RETENTION_DAYS} days")
    except Exception as e:
        print(f"[Cleanup] Error: {e}")

# Start background thread on app startup
threading.Thread(target=background_resource_collector, daemon=True).start()

# Mount static files after defining the root redirect, so '/' is not shadowed by static serving
@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")

app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/history", response_model=List[dict])
def get_history_endpoint(user: str = Depends(authenticate), days: int = 7):
    try:
        days = min(days, DATA_RETENTION_DAYS)
        history_data = get_history(days)
        if not history_data:
            print("No history data returned from db_utils.get_history()")
        return history_data
    except Exception as e:
        print(f"History endpoint error: {e}")
        return []

@app.get("/current_status")
def test_alert(user: str = Depends(authenticate)):
    try:
        # Get current status
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        # Send current status
        send_alert_email(
            subject="Current System Resource status",
            body="Current system status.",
            cpu=cpu,
            mem=mem,
            disk=disk
        )
        return {"status": "success", "message": "Current system status sent over email"}
    except Exception as e:
        print(f"Test alert error: {e}")
        return {"status": "error", "message": str(e)}

# Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
if __name__ == "__main__":
    print("Please run the server using: uvicorn main:app --host 0.0.0.0 --port 8000 --reload")

