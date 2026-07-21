# mew/config.py
"""
Hardcoded configuration for the Meowie automation module.
Edit this file directly — there is no runtime override.
"""

# === Target groups with priorities ===
# هر گروهی که میخوای ربات توش فعال باشه رو اینجا بذار
GROUPS = [ 
        
    {
        # Pishi Abad
        "id": -1004290700072,
        "auto_mew_min": 250,   # 5 minutes
        "auto_mew_max": 500,
        "fish_min": 2700,
        "fish_max": 3300
    },
    {
        # Mewoie Gap
        "id": -1004428268683,
        "auto_mew_min": 300,
        "auto_mew_max": 500,
        "fish_min": 3000,
        "fish_max": 3600
    },
    {
        # shack
        "id": -1004447898413,
        "auto_mew_min": 300,
        "auto_mew_max": 500,
        "fish_min": 3600,
        "fish_max": 4200
    }
]

# === Mew word pool (random pick per send) ===
MEW_WORDS = ["مع", "میو", "معو"]

# === Startup Delay ===
MAX_STARTUP_DELAY = 60

# === Meowie Bot IDs ===
MEOWIE_BOT_IDS = [
    8024943840,
    8239521948,
]

# === Collect timing (seconds) ===
COLLECT_THRESHOLD = 0.7      # Collect when points reach 70% of capacity
COLLECT_MIN_INTERVAL = 600   # 10 minutes
COLLECT_MAX_INTERVAL = 900   # 15 minutes

# === Unified Retry Logic ===
REPLY_MAX_ATTEMPTS = 20       
REPLY_POLL_INTERVAL = 5       
BUTTON_MAX_ATTEMPTS = 30      
BUTTON_POLL_INTERVAL = 7      
BUTTON_VERIFY_DELAY = 5       

# === Reconcile loop cadence ===
RECONCILE_INTERVAL = 20

# === Backoff used by BaseTask ===
CRASH_BACKOFF_SECONDS = 30

# === Paths ===
import os
_MEW_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_MEW_DIR, "mew.db")