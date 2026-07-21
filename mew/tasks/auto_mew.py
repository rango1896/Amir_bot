# mew/tasks/auto_mew.py
import asyncio
import random
import logging

from telethon.errors import FloodWaitError

from .base_task import BaseTask
from .. import config

logger = logging.getLogger("mew.tasks.auto_mew")


class AutoMewTask(BaseTask):
    name = "auto_mew"
    default_enabled = True

    async def loop(self, account_id: str, client):
        while True:
            # Pick a group config which contains its own sleep intervals
            target_group = random.choice(config.GROUPS)
            
            sleep_time = random.randint(
                target_group["auto_mew_min"],
                target_group["auto_mew_max"],
            )
            minutes, seconds = divmod(sleep_time, 60)
            logger.info("[auto_mew] %s next mew in %dm %ds (Group: %s)", account_id, minutes, seconds, target_group["id"])

            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                raise

            if not client.is_connected():
                logger.warning("[auto_mew] %s client disconnected — exiting loop", account_id)
                return

            message = random.choice(config.MEW_WORDS)

            try:
                await client.send_message(target_group["id"], message)
                logger.info("[auto_mew] %s mewed: %s", account_id, message)
            except FloodWaitError as e:
                wait = getattr(e, 'seconds', 60)
                logger.warning("[auto_mew] %s FloodWait %ss — sleeping", account_id, wait)
                await asyncio.sleep(wait + 5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("[auto_mew] %s send error: %s — sleeping 60s", account_id, e)
                await asyncio.sleep(60)
