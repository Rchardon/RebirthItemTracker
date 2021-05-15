import os
os.chdir("updater-lib")
try:
    os.execlp("updater.exe", "Rebirth Item Tracker")
except:
    os.execl("updater.exe", "Rebirth Item Tracker")