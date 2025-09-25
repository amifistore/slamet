import os
from dotenv import load_dotenv

load_dotenv()

def get_config():
    return {
        "TOKEN": os.getenv("TELEGRAM_TOKEN"),
        "ADMIN_IDS": [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i],
        "BASE_URL": os.getenv("PROVIDER_BASE_URL", "https://panel.khfy-store.com/api_v2/"),
        "API_KEY": os.getenv("PROVIDER_API_KEY"),
        "QRIS_STATIS": os.getenv("QRIS_STATIS"),
        "WEBHOOK_URL": os.getenv("WEBHOOK_URL"),
        "WEBHOOK_PORT": int(os.getenv("WEBHOOK_PORT", 8080)),
        "LOG_FILE": os.getenv("LOG_FILE", "bot_error.log"),
        "ENV": os.getenv("ENV", "development"),
    }
