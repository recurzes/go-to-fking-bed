import psutil
import os
import time
import random
from datetime import datetime, timedelta

CRITICAL_PROCESSES = {
    'system', 'smss.exe', 'csrss.exe', 'wininit.exe', 'services.exe',
    'lsass.exe', 'winlogon.exe', 'svchost.exe', 'dwm.exe', 'explorer.exe',
    'taskmgr.exe', 'logonui.exe', 'fontdrvhost.exe', 'conhost.exe',
    'registry', 'memory compression', 'idle', 'secure system',
    'system interrupts', 'wudfhost.exe', 'spoolsv.exe', 'audiodg.exe'
}

PROTECTED_SERVICES = {
    'runtimebroker.exe', 'sihost.exe', 'ctfmon.exe', 'taskhostw.exe',
    'searchindexer.exe', 'searchhost.exe', 'startmenuexperiencehost.exe',
    'shellexperiencehost.exe', 'textinputhost.exe', 'dllhost.exe',
    'wudfrd.exe', 'wudfhost.exe'
}

TARGET_HOUR = 22
TARGET_MINUTE = 00


def is_safe_to_terminate(proc):
    try:
        proc_name = proc.name().lower()

        if proc_name in CRITICAL_PROCESSES:
            return False

        if proc_name in PROTECTED_SERVICES:
            return False

        try:
            username = proc.username()
            if username and (
                    'SYSTEM' in username.upper() or 'LOCAL SERVICE' in username.upper() or 'NETWORK SERVICE' in username.upper()):
                return False

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

        if 'python' in proc_name and proc.id == os.getpid():
            return False

        return True

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def close_user_applications():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting to close user applications...")
    closed_count = 0
    skipped_count = 0

    processes = list(psutil.process_iter(['pid', 'name']))

    for proc in processes:
        try:
            if is_safe_to_terminate(proc):
                proc_name = proc.name()
                print(f"ClosingL {proc_name} (PID: {proc.pid})")

                proc.terminate()

                try:
                    proc.wait(timeout=3)
                    print(f"Closed gracefully: {proc_name}")
                except psutil.TimeoutExpired:
                    proc.kill()
                    print(f"Force closed: {proc_name}")

                closed_count += 1

                delay = random.uniform(1, 3)
                time.sleep(delay)

            else:
                skipped_count += 1

        except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
            pass

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Application closing complete.")
    print(f"  Closed: {closed_count} applications")
    print(f"  Protected: {skipped_count} system processes")


def wait_until_shutdown_time(target_hour=22, target_minute=0):
    now = datetime.now()
    target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

    if now >= target_time:
        target_time += timedelta(days=1)

    time_difference = (target_time - now).total_seconds()

    print(f"\n{'=' * 60}")
    print(f"Scheduled Shutdown System - Windows")
    print(f"{'=' * 60}")
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Shutdown scheduled for: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(
        f"Time until shutdown: {int(time_difference // 3600)}h {int((time_difference % 3600) // 60)}m {int(time_difference % 60)}s")
    print(f"{'=' * 60}\n")

    print("Waiting for shutdown time...")
    print("Press Ctrl+C to cancel\n")

    try:
        time.sleep(time_difference)
    except KeyboardInterrupt:
        print("\n\nShutdown cancelled by user.")
        exit(0)


def shutdown_system():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Initiating system shutdown...")
    print("System will shut down in 30 seconds.")

    os.system(f"shutdown /s /t 30 /c \"Scheduled shutdown at {TARGET_HOUR}:{TARGET_MINUTE}\"")

def main():
    wait_until_shutdown_time(target_hour=TARGET_HOUR, target_minute=TARGET_MINUTE)

    close_user_applications()

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Preparing for system shutdown...")
    time.sleep(5)

    shutdown_system()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Shutdown initiated successfully.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScript terminated by user")
    except Exception as e:
        print(f"\nError occurred: {e}")
        input("Press Enter to exit...")
