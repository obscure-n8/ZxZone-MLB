import time
import shutil
import psutil

def get_progress_bar(percentage):
    total_blocks = 12
    filled = int(percentage / (100 / total_blocks))
    bar = "■" * filled
    if filled < total_blocks:
        bar += "▩" + "□" * (total_blocks - filled - 1)
    return f"╭[{bar}] {percentage:.2f}%"

def get_readable_size(size):
    if not size: return "0B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024: return f"{size:.2f}{unit}"
        size /= 1024

def get_readable_time(seconds):
    if seconds <= 0: return "0s"
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    res = ""
    for name, count in periods:
        value = seconds // count
        if value:
            seconds %= count
            res += f"{int(value)}{name}"
    return res

def generate_status_text(task):
    processed = task.get('processed', 0)
    total = task.get('total', 0)
    speed = task.get('speed', 1)
    elapsed = time.time() - task.get('start_time', time.time())
    
    percentage = (processed / total) * 100 if total > 0 else 0
    eta = (total - processed) / speed if speed > 0 else 0
    
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    _, _, free_b = shutil.disk_usage(".")
    
    msg = f"1. File Name: {task.get('name')}\n"
    msg += f"{get_progress_bar(percentage)}\n"
    msg += f"├ Processed: {get_readable_size(processed)}\n"
    msg += f"├ Total: {get_readable_size(total)}\n"
    msg += f"├ Status: {task.get('status')}\n"
    msg += f"├ ETA: {get_readable_time(eta)}\n"
    msg += f"├ Speed: {get_readable_size(speed)}/s\n"
    msg += f"├ Elapsed: {get_readable_time(elapsed)}\n"
    msg += f"├ Engine: {task.get('engine')}\n"
    msg += f"├ In Mode: {task.get('in_mode')}\n"
    msg += f"├ Out Mode: {task.get('out_mode')}\n"
    msg += f"├ User: {task.get('user')}\n"
    msg += f"╰ Cancel: /cancel_{task.get('id')}\n\n"
    
    msg += "⌬ Bot Stats\n"
    msg += f"╭ Tasks: 1\n"
    msg += f"├ CPU: {cpu}%\n"
    msg += f"├ RAM: {ram}%\n"
    msg += f"╰ Free: {get_readable_size(free_b)}  | Uptime: {get_readable_time(elapsed)}"
    return msg
