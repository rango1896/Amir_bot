# mew/tasks/collect.py
import asyncio
import random
import re
import logging

from telethon.errors import FloodWaitError, RPCError

from .base_task import BaseTask, NoAvailableChat
from .. import config

logger = logging.getLogger("mew.tasks.collect")


class CollectTask(BaseTask):
    name = "collect"
    default_enabled = True

    async def loop(self, account_id: str, client):
        while True:
            try:
                await self._do_collect(account_id, client)
            except NoAvailableChat:
                logger.error("[collect] %s has no reachable chat left. Stopping collect task.", account_id)
                return

            sleep_time = random.randint(
                config.COLLECT_MIN_INTERVAL,
                config.COLLECT_MAX_INTERVAL,
            )
            minutes, seconds = divmod(sleep_time, 60)
            logger.info("[collect] %s next status check in %dm %ds", account_id, minutes, seconds)

            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                raise

    async def _do_collect(self, account_id: str, client):
        try:
            # 1. Send "پیشی" with failover and wait for the bot's NEW reply
            target_group, sent_msg = await self._send_with_failover(client, "پیشی", account_id)
            logger.info("[collect] %s sent 'پیشی' to %s, waiting for bot reply...", account_id, target_group["id"])

            reply_msg = await self._wait_for_bot_reply(client, target_group, sent_msg.id)
            
            if not reply_msg:
                logger.warning("[collect] %s bot did not reply to collect command.", account_id)
                return

            # 2. Parse stats from the fresh reply
            stats = self._parse_stats(reply_msg.message)
            if not stats:
                logger.error("[collect] %s failed to parse stats from message:\n%s", account_id, reply_msg.message)
                return

            current, speed, capacity = stats
            target = int(capacity * config.COLLECT_THRESHOLD)

            # 3. If capacity reached, click the button on that exact reply message
            if current >= target:
                logger.info("[collect] %s capacity reached (%d/%d). Clicking button now!", account_id, current, capacity)
                clicked = await self._wait_and_click_button(client, target_group, reply_msg.id, ["برداشت"])
                if clicked:
                    logger.info("[collect] %s successfully collected points.", account_id)
                else:
                    logger.warning("[collect] %s failed to click collect button. Will retry next cycle.", account_id)
            else:
                points_needed = target - current
                est_mins = (points_needed / speed) / 60 if speed > 0 else float('inf')
                logger.info(
                    "[collect] %s stats: %d/%d points. Est. time to fill: %.1f mins. Will recheck later.",
                    account_id, current, target, est_mins
                )

        except NoAvailableChat:
            raise
        except FloodWaitError as e:
            wait = getattr(e, 'seconds', 60)
            logger.warning("[collect] %s FloodWait %ss during collect. Sleeping.", account_id, wait)
            await asyncio.sleep(wait + 5)
        except Exception as e:
            logger.exception("[collect] %s unexpected error during collect: %s", account_id, e)

    def _parse_stats(self, text: str) -> tuple[int, float, int] | None:
        try:
            # Strip thousands separators AND the backticks Telegram markdown
            clean_text = (
                text.replace(",", "")
                    .replace("،", "")
                    .replace("`", "")
            )
            current_match = re.search(r"تولید شده\s*:\s*(\d+)", clean_text)
            # Updated regex to handle float speeds like 4.5
            speed_match = re.search(r"ثانیه\s*:\s*(\d+\.?\d*)", clean_text)
            cap_match = re.search(r"ظرفیت\s*:\s*(\d+)", clean_text)

            if not (current_match and speed_match and cap_match):
                return None

            return int(current_match.group(1)), float(speed_match.group(1)), int(cap_match.group(1))
        except Exception as e:
            logger.error("[collect] Error parsing stats: %s", e)
            return None
