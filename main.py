import platform

import psutil
import os
import time
import random
from datetime import datetime, timedelta

CURRENT_OS = platform.system()
TARGET_HOUR = 14
TARGET_MINUTE = 00

if CURRENT_OS == "Windows":
    try:
        import win32gui
        import win32process
        import win32con
        PYWIN32_AVAILABLE = True
    except ImportError:
        PYWIN32_AVAILABLE = False
        print("Warning pywin32 not installed")
        print("For better accuracy, install: pip install pywin32\n")
else:
    PYWIN32_AVAILABLE = False


# Functions
def get_gui_windows_pywin32():
    gui_apps = {}

    def enum_window_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)

            if not title:
                return

            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

            if style & win32con.WS_VISIBLE and not (ex_style & win32con.WS_EX_TOOLWINDOW):

                _, pid = win32process.GetWindowThreadProcessId(hwnd)

                if pid not in results:
                    results[pid] = title

    try:
        win32gui.EnumWindows(enum_window_callback, gui_apps)
    except Exception as e:
        print(f"Error enumerating windows: {e}")

    return gui_apps


def has_visible_window_windows(proc):
    if PYWIN32_AVAILABLE:
        gui_windows = get_gui_windows_pywin32()
        return proc.pid in gui_windows
    else:
        try:
            username = proc.username()
            current_user = os.environ.get("USERNAME", '')
            return proc.num_threads() > 1 and username and current_user.lower() in username.lower()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return False


def has_visible_window_linux(proc):
    try:
        env = proc.environ()
        if 'DISPLAY' in env or 'WAYLAND_DISPLAY' in env:
            proc_name = proc.name().lower()

            gui_patterns = [
                'chrome', 'firefox', 'brave', 'edge', 'opera', 'vivaldi',
                'code', 'atom', 'sublime', 'gedit', 'kate', 'geany',
                'libreoffice', 'gimp', 'inkscape', 'blender',
                'discord', 'slack', 'telegram', 'signal', 'zoom',
                'spotify', 'vlc', 'mpv', 'totem',
                'nautilus', 'dolphin', 'thunar', 'pcmanfm', 'nemo',
                'calculator', 'gnome-', 'kde-', 'plasma-',
                'thunderbird', 'evolution', 'geary' # Add some more depending on preferences
            ]

            return any(pattern in proc_name for pattern in gui_patterns)
        return False
    except (psutil.AccessDenied, psutil.NoSuchProcess, KeyError):
        return False


def has_visible_window_macos(proc):
    try:
        proc_name = proc.name().lower()

        gui_patterns = [
            'safari', 'chrome', 'firefox', 'brave', 'edge', 'opera',
            'code', 'xcode', 'atom', 'sublime', 'textedit',
            'pages', 'numbers', 'keynote', 'office', 'word', 'excel', 'powerpoint',
            'discord', 'slack', 'telegram', 'signal', 'zoom', 'facetime',
            'spotify', 'music', 'itunes', 'vlc', 'quicktime',
            'photos', 'preview', 'mail', 'messages',
            'notes', 'reminders', 'calendar', 'contacts',
            'calculator', 'activity monitor'
        ]

        if any(pattern in proc_name for pattern in gui_patterns):
            return True

        try:
            exe = proc.exe()
            if '/Applications/' in exe and '.app/' in exe:
                return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

        return False
    except (psutil. AccessDenied, psutil.NoSuchProcess):
        return False


def is_gui_application(proc):
    try:
        proc_name = proc.name().lower()

        system_excluded = [
            'system', 'registry', 'csrss.exe', 'smss.exe', 'services.exe',
            'lsass.exe', 'winlogon.exe', 'svchost.exe', 'explorer.exe',
            'dwm.exe', 'systemd', 'init', 'launchd', 'kernel_task',
            'windowserver', 'loginwindow', 'finder', 'dock'
        ]

        if proc_name in system_excluded:
            return False

        if 'python' in proc_name and proc.pid == os.getpid():
            return False

        if CURRENT_OS == 'Windows':
            return has_visible_window_windows(proc)
        elif CURRENT_OS == "Linux":
            return has_visible_window_linux(proc)
        elif CURRENT_OS == "Darwin":
            return has_visible_window_macos(proc)

        return False

    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return False


def close_application_gracefully_windows(proc, window_title):
    if not PYWIN32_AVAILABLE:
        proc.terminate()
        return False

    try:
        def find_window_callback(hwnd, target_pid):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid == target_pid:
                if win32gui.IsWindowVisible(hwnd):
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    return False

            return True

        win32gui.EnumWindows(lambda hwnd, pid: find_window_callback(hwnd, pid), proc.pid)
        return True
    except Exception:
        proc.terminate()
        return False


def close_gui_applications():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting to close GUI applications...")
    print(f"    (Only closing apps from 'Apps' tab, not background processes)\n")

    closed_count = 0
    close_apps = []

    if CURRENT_OS == 'Windows' and PYWIN32_AVAILABLE:
        gui_windows = get_gui_windows_pywin32()
        print(f"Found {len(gui_windows)} GUI applications with visible windows\n")

        for pid, title in gui_windows.items():
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()

                if proc_name.lower() in ['explorer.exe', 'dwm.exe', 'taskmgr.exe']:
                    continue

                print(f"    Closing: {proc_name} - '{title}' (PID: {pid})")

                close_application_gracefully_windows(proc, title)

                try:
                    proc.wait(timeout=3)
                    print(f"Closed gracefully: {proc_name}")

                except psutil.TimeoutExpired:
                    proc.kill()
                    print(f"Force closed: {proc_name}")

                closed_count += 1
                close_apps.append(proc_name)

                delay = random.uniform(1, 3)
                time.sleep(delay)

            except (psutil.AccessDenied, psutil.NoSuchProcess, PermissionError):
                pass

    else:
        processes = list(psutil.process_iter(['pid', 'name']))

        for proc in processes:
            try:
                if is_gui_application(proc):
                    proc_name = proc.name()
                    print(f"Closing: {proc_name} (PID: {proc.pid})")

                    proc.terminate()

                    try:
                        proc.wait(timeout=3)
                        print(f"Closed gracefully: {proc_name}")
                        close_apps.append(proc_name)
                    except psutil.TimeoutExpired:
                        proc.kill()
                        print(f"Force closed: {proc_name}")
                        close_apps.append(proc_name)

                    closed_count += 1

                    delay = random.uniform(1, 3)
                    time.sleep(delay)

            except (psutil.AccessDenied, psutil.NoSuchProcess, PermissionError):
                pass

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Application closing complete.")
    print(f"  Closed {closed_count} GUI applications")

    if close_apps:
        print(f"\n Apps closed: {', '.join(set(close_apps))}")


def wait_until_shutdown_time(target_hour=22, target_minute=0):
    now = datetime.now()
    target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

    if now >= target_time:
        target_time += timedelta(days=1)

    time_difference = (target_time - now).total_seconds()

    print(f"\n{'=' * 70}")
    print(f"Scheduled Shutdown System - {CURRENT_OS}")
    if CURRENT_OS == 'Windows' and PYWIN32_AVAILABLE:
        print(f"Using pywin32 for accurate GUI detection")
    print(f"\n{'=' * 70}")
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Shutdown scheduled for: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Time until shutdown: {int(time_difference // 3600)}h {int((time_difference % 3600) // 60)}m {int(time_difference % 60)}s")
    print(f"\n{'=' * 70}")

    print("Script is now running in the foreground")
    print("It will wait until 10PM to close GUI apps and shutdown")
    print("Press Ctrl+C to cancel\n")

    try:
        remaining = time_difference
        last_update = time.time()

        while remaining > 0:
            sleep_time = min(300, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time

            if remaining > 60 and time.time() - last_update >= 300:
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Still waiting... {hours}h {minutes}m remaining")
                last_update = time.time()

    except KeyboardInterrupt:
        print("\n\nShutdown cancelled by user")
        exit(0)


def shutdown_system():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Intiating system shutdown....")
    message = f"Scheduled shutdown at {TARGET_HOUR}:{TARGET_MINUTE}"

    if CURRENT_OS == 'Windows':
        print("System will shut down in 30 seconds.")
        os.system(f'shutdown /s /t 30 /c "{message}"')

    if CURRENT_OS == 'Linux':
        print("System will shut down in 1 minute")
        print("Note: This requires sudo privileges")
        os.system(f"shutdown -h +1 '{message}'")

    elif CURRENT_OS == 'Darwin':
        print('System will shut down in 1 minute')
        print("Note: This requires sudo privileges")
        os.system(f"sudo shutdown -h +1 '{message}'")

    else:
        print(f"Error: Unsupported operating system '{CURRENT_OS}'")
        return


def check_privileges():
    if CURRENT_OS in ['Linux', 'Darwin']:
        if os.geteuid() != 0:
            print(f"\nWarning: Running on {CURRENT_OS} without root privileges")
            print("The scripts can close applications but may not shutdown the system")
            print(f"To enable shutdown, run: sudo python3 {os.path.basename(__file__)}\n")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Exiting...")
                exit(0)


def main():
    print(f"\nDetected Operating System: {CURRENT_OS}")
    print(f"Target: Close GUI applications only (Apps tab equivalent)\n")

    if CURRENT_OS == 'Windows':
        if PYWIN32_AVAILABLE:
            print("pywin32 detected - Using accurate Windows GUI detection")
        else:
            print("pywin32 not installed")
            print("Install for better accuracy: pip install pywin32")
        print()

    check_privileges()

    wait_until_shutdown_time(target_hour=TARGET_HOUR, target_minute=TARGET_MINUTE)

    close_gui_applications()

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Preparing for system shutdown...")
    time.sleep(5)

    shutdown_system()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Shutdown initiated successfully.")
    print("\nYou can now close this window or wait for shutdown to complete.")



if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScript terminated by user")
    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")