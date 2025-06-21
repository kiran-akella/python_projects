import sqlite3
from datetime import datetime, timedelta
import psutil

DB_PATH = 'resource_data.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS resource_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        cpu_percent REAL,
        memory_percent REAL,
        disk_percent REAL,
        disk_read_bytes INTEGER DEFAULT 0,
        disk_write_bytes INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def store_resource_usage(cpu, mem, disk):
    io = psutil.disk_io_counters()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)  # Add timeout
        c = conn.cursor()
        c.execute('''INSERT INTO resource_usage (timestamp, cpu_percent, memory_percent, disk_percent, disk_read_bytes, disk_write_bytes)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (datetime.now().isoformat(), cpu, mem, disk, io.read_bytes, io.write_bytes))
        conn.commit()
    except Exception as e:
        print(f"Error storing resource usage: {e}")
    finally:
        conn.close()

def should_store_new_entry():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT timestamp FROM resource_usage ORDER BY id DESC LIMIT 1''')
    last = c.fetchone()
    conn.close()
    if not last:
        return True
    last_time = datetime.fromisoformat(last[0])
    return (datetime.now() - last_time).total_seconds() >= 5  # 5 seconds

def get_history(days=7):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get rows with disk I/O data
        c.execute('''
            SELECT timestamp, cpu_percent, memory_percent, disk_percent, disk_read_bytes, disk_write_bytes 
            FROM resource_usage 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        ''', (since,))
        
        rows = c.fetchall()
        result = []
        prev_row = None
        
        for row in rows:
            disk_io_mb_sec = 0.0
            if prev_row:
                try:
                    time_diff = (datetime.fromisoformat(row[0]) - datetime.fromisoformat(prev_row[0])).total_seconds()
                    read_diff = row[4] - prev_row[4]
                    write_diff = row[5] - prev_row[5]
                    
                    if time_diff > 0 and read_diff >= 0 and write_diff >= 0:
                        total_bytes = read_diff + write_diff
                        disk_io_mb_sec = (total_bytes / (1024 * 1024)) / time_diff
                except Exception as e:
                    print(f"Error calculating disk I/O: {e}")
            
            result.append({
                "timestamp": row[0],
                "cpu_percent": float(row[1]),
                "memory_percent": float(row[2]),
                "disk_percent": float(row[3]),
                "disk_io_mb_sec": round(max(0, disk_io_mb_sec), 2)
            })
            prev_row = row
        
        conn.close()
        return list(reversed(result))  # Return most recent first
        
    except Exception as e:
        print(f"Database error in get_history: {e}")
        return []

def get_averages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT AVG(cpu_percent), AVG(memory_percent), AVG(disk_percent) FROM resource_usage''')
    avg_cpu, avg_mem, avg_disk = c.fetchone()
    conn.close()
    return avg_cpu, avg_mem, avg_disk
