import psutil
import os
import time
import random
from datetime import datetime, timedelta

CRITICAL_PROCESSES = {
    'kernel_task', 'launchd', 'kernelmanagerd', 'syslogd',
    'kextd', 'configd', 'powerd', 'logd', 'UserEventAgent',
    'diskarbitrationd', 'notifyd', 'securityd', 'opendirectoryd',
    'mds', 'mds_stores', 'mdworker', 'cfprefsd', 'trustd',
    'WindowServer', 'loginwindow', 'systemstats', 'coreauthd',
    'coreservicesd', 'finder', 'dock', 'systemuiserver',
    'controlcenter', 'airplayd', 'bluetoothd', 'wifid',
    'discoveryd', 'mDNSResponder', 'networkd', 'symptomsd',
    'apsd', 'cloudd', 'bird', 'sharingd', 'universalaccessd',
    'hidd', 'fontd', 'iconservicesd', 'iconservicesagent',
    'coreduetd', 'dasd', 'CoreServicesUIAgent', 'talagent',
    'ScopedBookmarkAgent', 'ctkd', 'tccd', 'kbd', 'AssetCacheLocatorService',
    'installd', 'softwareupdated', 'nsurlsessiond', 'CommCenter',
    'mediaremoted', 'biometrickitd', 'audiomxd', 'coreaudiod',
    'backupd', 'TimeMachine', 'fseventsd', 'filecoordinationd',
    'displaypolicyd', 'dpd', 'rapportd', 'nesessionmanager',
    'fileproviderd', 'quicklookd', 'launchservicesd', 'lsd',
    'bluetoothaudiod', 'SystemUIServer', 'NotificationCenter'
}

PROTECTED_PATTERNS = [
    'com.apple.', 'kernel', 'launchd', 'system', 'login'
]

TARGET_HOUR = 22
TARGET_MINUTE = 00

def is_safe_to_terminate(proc):
    try:
        proc_name = proc.name().lower()

        if proc_name in CRITICAL_PROCESSES:
            return False

        for pattern in PROTECTED_PATTERNS:
            if pattern in proc_name:
                return False

        try:
            username = proc.username()
            if username and (username == 'root' or username.startswith('_') or username in ['daemon', 'nobody']):
                return False

        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return False

        try:
            if proc.ppid() in [0, 1]:
                if proc.ppid() == 1:
                    user_apps = ['safari', 'chrome', 'firefox', 'edge', 'opera',
                               'slack', 'discord', 'telegram', 'spotify',
                               'vlc', 'iterm', 'visual studio code', 'code',
                               'sublime', 'atom', 'pycharm', 'intellij']

                    if not any(app in proc_name for app in user_apps):
                        return False


        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return False

        if 'python' in proc_name and proc.pid == os.getpid():
            return False

        if proc_name in ['terminal', 'iterm2', 'iterm', 'kitty', 'alacritty',
                        'bash', 'zsh', 'fish', 'sh', 'terminal.app']:
            return False

        if proc_name in ['finder', 'dock']:
            return False

        return True

    except (psutil.AccessDenied, psutil.NoSuchProcess):
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
                print(f"Closing: {proc_name} (PID: {proc.pid})")

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


        except (psutil.AccessDenied, psutil.NoSuchProcess, PermissionError):
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
    print(f"Scheduled Shutdown System - macOS")
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
    print("System will shut down in 1 minute.")

    os.system(f"sudo shutdown -h +1 'Scheduled shutdown at {TARGET_HOUR}:{TARGET_MINUTE}")


def main():
    if os.geteuid() != 0:
        print("Warning: This script should be run with sudo privileges to shutdown the system")
        print("Example: sudo python3 shutdown_macos.py\n")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            return


    wait_until_shutdown_time(target_hour=TARGET_HOUR, target_minute=TARGET_MINUTE)

    close_user_applications()

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Preparing for system shutdown...")
    time.sleep(5)

    shutdown_system()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Shutdown initiated successfully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScript terminated by user.")
    except Exception as e:
        print(f"\nError occurred: {e}")
        input("Press Enter to exit...")
