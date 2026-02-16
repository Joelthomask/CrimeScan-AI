import subprocess
import os
import sys

# Correct base path detection
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("BASE_DIR:", BASE_DIR)

python_exe = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
app_file = os.path.join(BASE_DIR, "app.py")

print("Python path:", python_exe)
print("App path:", app_file)

if not os.path.exists(python_exe):
    print("ERROR: python.exe not found!")
    input("Press ENTER to exit...")
    sys.exit()

print("Launching app...")

process = subprocess.Popen([python_exe, app_file])
process.wait()

print("App closed.")
input("Press ENTER to exit launcher...")
