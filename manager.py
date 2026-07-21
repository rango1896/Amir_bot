import asyncio
import json
import os
import logging
import signal
from telethon import TelegramClient

from mew import MewManager, register_mew_commands

logging.basicConfig(level=logging.WARNING,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AccountManager:
    def __init__(self, config_path="accounts.json"):
        self.config_path = config_path
        self.accounts = {}
        self.all_configs = {}        # all entries (running or not) — mew uses this
        self.last_mtime = 0
        self.mew_manager = None      # set later in main()

    async def start(self):
        await self.sync_accounts()
        asyncio.create_task(self.watch_config_file())

    async def watch_config_file(self):
        while True:
            try:
                mtime = os.path.getmtime(self.config_path)
                if mtime != self.last_mtime:
                    logger.info("[Manager] accounts.json changed. Syncing...")
                    if await self.sync_accounts():
                        self.last_mtime = mtime
            except FileNotFoundError:
                logger.error(f"[Manager] {self.config_path} not found.")
            except Exception:
                logger.exception("[Manager] watcher error - continuing.")
            await asyncio.sleep(5)

    async def sync_accounts(self) -> bool:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                new_configs = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"[Manager] Failed to read JSON: {e}")
            return False

        self.all_configs = new_configs
        new_ids = set(new_configs.keys())
        current_ids = set(self.accounts.keys())

        for acc_id in new_ids - current_ids:
            await self.start_account(acc_id, new_configs[acc_id])

        for acc_id in current_ids - new_ids:
            await self.stop_account(acc_id)

        for acc_id in new_ids & current_ids:
            client = self.accounts[acc_id]["client"]
            old_enabled = client.config.get("enabled", True)
            new_enabled = new_configs[acc_id].get("enabled", True)
            if old_enabled != new_enabled or client.config != new_configs[acc_id]:
                logger.info(f"[Manager] {acc_id} changed. Restarting.")
                await self.stop_account(acc_id)
                await self.start_account(acc_id, new_configs[acc_id])

        return True

    async def start_account(self, account_id, config):
        if account_id in self.accounts:
            return True

        logger.info(f"Starting account: {account_id}")
        try:
            os.makedirs("sessions", exist_ok=True)
            session_path = os.path.join("sessions", config["session_name"])
            session_file = f"{session_path}.session"

            if not os.path.exists(session_file):
                logger.error(f"[{account_id}] Session file missing: {session_file}")
                return False

            client = TelegramClient(session_path,
                                    config["api_id"], config["api_hash"])
            client.account_id = account_id
            client.config = config
            client.task_queue = asyncio.Queue()

            await client.connect()
            if not await client.is_user_authorized():
                logger.error(f"[{account_id}] Unauthorized session. Skipping.")
                await client.disconnect()
                return False

            # === Mew module — the only thing registered now ===
            if self.mew_manager is not None:
                register_mew_commands(client, self.mew_manager)

            worker = asyncio.create_task(self.queue_worker(client))
            self.accounts[account_id] = {
                "client": client,
                "worker": worker,
                "config": config,
            }
            logger.info(f"[{account_id}] Started successfully.")
            return True
        except Exception as e:
            logger.error(f"[{account_id}] Failed to start: {e}")
            return False

    async def stop_account(self, account_id):
        logger.info(f"Stopping account: {account_id}")
        acc_data = self.accounts.pop(account_id, {})
        if not acc_data:
            return

        worker = acc_data.get("worker")
        if worker and not worker.done():
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass

        client = acc_data.get("client")
        if client:
            while not client.task_queue.empty():
                try:
                    t = client.task_queue.get_nowait()
                    if asyncio.iscoroutine(t):
                        t.close()
                except Exception:
                    break
            await client.disconnect()
        logger.info(f"Account {account_id} stopped.")

    async def stop_all(self):
        logger.info("[Manager] Shutting down all sessions...")
        for acc_id in list(self.accounts.keys()):
            try:
                await self.stop_account(acc_id)
            except Exception as e:
                logger.error(f"[Manager] Error stopping {acc_id}: {e}")

    async def queue_worker(self, client):
        while True:
            try:
                task_coro = await client.task_queue.get()
                await task_coro
                delay = client.config.get("queue_delay", 0.5)
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(f"[{client.account_id}] Queue worker failure")

# === Keep Render awake with a web server ===
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "OK"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_flask, daemon=True).start()
if __name__ == '__main__':
    async def main():
        manager = AccountManager("accounts.json")

        # === Start Mew module ===
        mew_manager = MewManager(manager)
        await mew_manager.start()
        manager.mew_manager = mew_manager

        await manager.start()

        stop_event = asyncio.Event()
        def shutdown():
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, shutdown)

        print("Manager & Mew module started. Press Ctrl+C to stop.")
        await stop_event.wait()

        await manager.stop_all()
        await mew_manager.stop()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete.")
