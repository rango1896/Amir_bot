# mew/config.py
"""
Hardcoded configuration for the Meowie automation module.
Edit this file directly — there is no runtime override.
"""

# === Target groups with priorities ===
# Each group has its own auto-mew sleep values.
# The accounts will randomly pick from this list, and the chosen group
# dictates how long they sleep before sending the next command.
GROUPS = [
        
    {
        # Pishi Abad
        "id": -1004448320446,
        "auto_mew_min": 250,   # 5 minutes
        "auto_mew_max": 500,
        "fish_min": 2700,
        "fish_max": 3300
    },
    {
        # Mewoie Gap
        "id": -1004428268683,
        "auto_mew_min": 300,   # 5 minutes
        "auto_mew_max": 500,
        "fish_min": 3000,
        "fish_max": 3600
    }
]

# === Mew word pool (random pick per send) ===
MEW_WORDS = ["مع", "میو", "معو"]

# === Startup Delay ===
MAX_STARTUP_DELAY = 60

# === Meowie Bot IDs (the bot has mirrors, so we check against any) ===
MEOWIE_BOT_IDS = [
    8024943840,
    8239521948,
    8299996037,
    8839105739,
    8948063973,
]

# === Collect timing (seconds) ===
COLLECT_THRESHOLD = 0.6      # Collect when points reach 70% of capacity
COLLECT_MIN_INTERVAL = 1000
COLLECT_MAX_INTERVAL = 1600 

# === Unified Retry Logic (used by both Fishing and Collect) ===
REPLY_MAX_ATTEMPTS = 20       # Try 20 times to find the bot's reply
REPLY_POLL_INTERVAL = 5       # Wait 5s between each attempt (100s total)
BUTTON_MAX_ATTEMPTS = 30      # Try 30 times to find/click the button
BUTTON_POLL_INTERVAL = 7      # Wait 5s between each attempt (150s total)
BUTTON_VERIFY_DELAY = 5       # Wait 3s after clicking to verify it disappeared

# === Reconcile loop cadence ===
RECONCILE_INTERVAL = 20

# === Backoff used by BaseTask when a per-user loop crashes unexpectedly. ===
CRASH_BACKOFF_SECONDS = 30

# === Paths ===
import os
_MEW_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_MEW_DIR, "mew.db")