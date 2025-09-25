import shutil
import os
from datetime import datetime

def backup_sqlite(dbfile='botdata.db', backup_dir='backup'):
    os.makedirs(backup_dir, exist_ok=True)
    date = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{backup_dir}/botdata_{date}.db"
    shutil.copy(dbfile, dst)
    print(f"Backup selesai ke {dst}")

if __name__ == "__main__":
    backup_sqlite()
