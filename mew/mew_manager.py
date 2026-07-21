# mew/mew_manager.py
import asyncio
import logging

from . import config
from .mew_db import MewDB
from .tasks import AutoMewTask, FishingTask, CollectTask, BaseTask

logger = logging.getLogger("mew.manager")


class MewManager:
    def __init__(self, account_manager):
        self.account_manager = account_manager
        self.db = MewDB()
        self.tasks: list[BaseTask] = []
        self._reconcile_task: asyncio.Task | None = None

    async def start(self):
        await self.db.init()
        self.tasks = [
            AutoMewTask(self),
            CollectTask(self),
            FishingTask(self),
        ]
        self._reconcile_task = asyncio.create_task(self._reconcile_loop())
        logger.info("[MewManager] started with %d task plugin(s)", len(self.tasks))

    async def stop(self):
        if self._reconcile_task and not self._reconcile_task.done():
            self._reconcile_task.cancel()
            try:
                await self._reconcile_task
            except asyncio.CancelledError:
                pass
        for task in self.tasks:
            await task.stop_all()
        await self.db.close()

    async def _reconcile_loop(self):
        while True:
            try:
                added = await self.db.list_added()
                added_ids = {acc_id for acc_id, _ in added}
                running = self.account_manager.accounts

                for account_id in added_ids:
                    acc_data = running.get(account_id)
                    if not acc_data:
                        for task in self.tasks:
                            await task.stop_for(account_id)
                        continue
                    
                    client = acc_data.get("client")
                    if not client or not client.is_connected():
                        continue
                    
                    for task in self.tasks:
                        is_enabled = await self.db.is_task_enabled(account_id, task.name, task.default_enabled)
                        if is_enabled:
                            await task.ensure_running(account_id, client)
                        else:
                            await task.stop_for(account_id)

                for task in self.tasks:
                    for account_id in list(task.user_tasks.keys()):
                        if account_id not in added_ids:
                            await task.stop_for(account_id)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("[MewManager] reconcile error: %s", e)

            try:
                await asyncio.sleep(config.RECONCILE_INTERVAL)
            except asyncio.CancelledError:
                raise

    async def add_user(self, identifier: str) -> tuple[bool, str]:
        if not self.account_manager.all_configs:
            return False, "accounts.json not loaded yet"

        match_id = None
        match_session = None
        for acc_id, cfg in self.account_manager.all_configs.items():
            if acc_id == identifier:
                match_id = acc_id
                match_session = cfg.get("session_name", acc_id)
                break
            if cfg.get("session_name") == identifier:
                match_id = acc_id
                match_session = cfg.get("session_name")
                break

        if not match_id:
            return False, f"Account '{identifier}' not found in accounts.json"

        await self.db.add_user(match_id, match_session or match_id)
        logger.info("[MewManager] added user %s (session=%s)", match_id, match_session)

        acc_data = self.account_manager.accounts.get(match_id)
        if acc_data:
            client = acc_data.get("client")
            if client and client.is_connected():
                for task in self.tasks:
                    is_enabled = await self.db.is_task_enabled(match_id, task.name, task.default_enabled)
                    if is_enabled:
                        await task.ensure_running(match_id, client)

        return True, (f"✅ Added `{match_id}` (session: `{match_session}`) "
                      f"to the mew cycle.")

    async def remove_user(self, identifier: str) -> tuple[bool, str]:
        match_id = None
        for acc_id, cfg in self.account_manager.all_configs.items():
            if acc_id == identifier or cfg.get("session_name") == identifier:
                match_id = acc_id
                break
        if not match_id:
            added = await self.db.list_added()
            for acc_id, _ in added:
                if acc_id == identifier:
                    match_id = acc_id
                    break

        if not match_id:
            return False, f"'{identifier}' is not in the mew cycle."

        for task in self.tasks:
            await task.stop_for(match_id)
        await self.db.remove_user(match_id)
        logger.info("[MewManager] removed user %s", match_id)
        return True, f"✅ Removed `{match_id}` from the mew cycle."

    async def list_users(self) -> list[dict]:
        added = await self.db.list_added()
        running = self.account_manager.accounts
        result = []
        for acc_id, session_name in added:
            is_online = acc_id in running
            task_states = {}
            for task in self.tasks:
                is_enabled = await self.db.is_task_enabled(acc_id, task.name, task.default_enabled)
                task_states[task.name] = "on" if is_enabled else "off"
            result.append({
                "account_id": acc_id,
                "session_name": session_name,
                "online": is_online,
                "tasks": task_states,
            })
        return result

    async def set_task_state(self, account_id: str, task_name: str, enabled: bool) -> tuple[bool, str]:
        await self.db.set_task_enabled(account_id, task_name, enabled)
        
        if not enabled:
            for task in self.tasks:
                if task.name == task_name:
                    await task.stop_for(account_id)
                    return True, f"✅ Turned OFF `{task_name}` for `{account_id}`."
        else:
            acc_data = self.account_manager.accounts.get(account_id)
            if acc_data:
                client = acc_data.get("client")
                if client and client.is_connected():
                    for task in self.tasks:
                        if task.name == task_name:
                            await task.ensure_running(account_id, client)
                            return True, f"✅ Turned ON `{task_name}` for `{account_id}`."
            return True, f"✅ Turned ON `{task_name}` for `{account_id}`. It will start when the account is online."
            
        return False, f"❌ Task `{task_name}` not found."

    def task_plugins(self) -> list[BaseTask]:
        return self.tasks