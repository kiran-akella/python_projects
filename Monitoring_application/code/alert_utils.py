import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
import io
from matplotlib import pyplot as plt

EMAILS_FILE = 'emails.json'
SMTP_FILE = 'smtp.json'

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

def generate_dashboard_snapshot(cpu, mem, disk):
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
