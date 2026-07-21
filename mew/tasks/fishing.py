# mew/tasks/fishing.py
import asyncio
import random
import re
import logging

from telethon.errors import FloodWaitError, RPCError

from .base_task import BaseTask, NoAvailableChat
from .. import config

logger = logging.getLogger("mew.tasks.fishing")


class FishingTask(BaseTask):
    name = "fishing"
    default_enabled = True

    async def loop(self, account_id: str, client):
        while True:
            try:
                success = await self._do_fishing(account_id, client)
            except NoAvailableChat:
                logger.error("[fishing] %s has no reachable chat left. Stopping fishing task.", account_id)
                return

            if success:
                logger.info("[fishing] %s successfully completed fishing cycle.", account_id)
            else:
                logger.warning("[fishing] %s fishing attempt failed.", account_id)

            target_group = random.choice(config.GROUPS)
            sleep_time = random.randint(
                target_group["fish_min"],
                target_group["fish_max"],
            )
            minutes, seconds = divmod(sleep_time, 60)
            logger.info("[fishing] %s next fishing attempt in %dm %ds", account_id, minutes, seconds)

            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                raise

    async def _do_fishing(self, account_id: str, client) -> bool:
        try:
            # 1. Check Hunger First
            target_group, sent_msg = await self._send_with_failover(client, "پیشی", account_id)
            reply_msg = await self._wait_for_bot_reply(client, target_group, sent_msg.id)
            if not reply_msg:
                logger.warning("[fishing] %s bot did not reply to hunger check.", account_id)
                return False

            current_hunger, max_hunger = self._parse_hunger(reply_msg.message)
            logger.info("[fishing] %s hunger: %d/%d", account_id, current_hunger, max_hunger)

            # 2. Start Fishing
            target_group, sent_msg = await self._send_with_failover(client, "ماهی", account_id)
            logger.info("[fishing] %s sent 'ماهی', waiting for bot reply...", account_id)
            reply_msg = await self._wait_for_bot_reply(client, target_group, sent_msg.id)

            if not reply_msg:
                logger.warning("[fishing] %s bot did not reply to fishing command.", account_id)
                return False

            fishing_msg_id = reply_msg.id
            logger.info("[fishing] %s locked onto bot reply (msg_id=%s). Watching it for edits...", account_id, fishing_msg_id)

            # Wait for the fishing animation to finish and panel to appear
            if not await self._wait_for_buttons(client, target_group, fishing_msg_id):
                logger.warning("[fishing] %s fishing buttons never appeared.", account_id)
                return False

            msg = await self._fetch_msg(client, target_group, fishing_msg_id)
            if not msg:
                return False

            has_fridge = any("بندازش تو یخچال" in btn.text for row in msg.buttons for btn in row)

            if has_fridge:
                logger.info("[fishing] %s has fridge. Storing fish...", account_id)
                if not await self._robust_click(client, target_group, fishing_msg_id, "بندازش تو یخچال"):
                    return False

                # 3. Open Fridge & Cook
                target_group, sent_msg = await self._send_with_failover(client, "یخچال میویی", account_id)
                reply_msg = await self._wait_for_bot_reply(client, target_group, sent_msg.id)
                if not reply_msg:
                    return False

                fridge_msg_id = reply_msg.id
                if not await self._wait_for_buttons(client, target_group, fridge_msg_id):
                    return False

                # Click the fish (ignore upgrade button)
                if not await self._click_first_non_upgrade(client, target_group, fridge_msg_id):
                    return False

                # Wait for cook button and click it
                if not await self._robust_click(client, target_group, fridge_msg_id, "بپوخش"):
                    return False

                # Fetch the new panel to parse cooking time
                msg = await self._fetch_msg(client, target_group, fridge_msg_id)
                cook_time = self._parse_cook_time(msg.message) if msg else 60
                logger.info("[fishing] %s cooking for %d seconds.", account_id, cook_time)

                # Click the confirm button (leftmost)
                if not await self._click_confirm(client, target_group, fridge_msg_id):
                    return False

                # Wait for cooking to finish
                await asyncio.sleep(cook_time)

                # 4. Collect Cooked Fish
                target_group, sent_msg = await self._send_with_failover(client, "یخچال میویی", account_id)
                reply_msg = await self._wait_for_bot_reply(client, target_group, sent_msg.id)
                if not reply_msg:
                    return False

                fridge_msg_id = reply_msg.id
                if not await self._wait_for_buttons(client, target_group, fridge_msg_id):
                    return False

                # Click the cooked fish (ignore upgrade)
                if not await self._click_first_non_upgrade(client, target_group, fridge_msg_id):
                    return False

                # The panel is now showing the cooked fish stats
                final_msg_id = fridge_msg_id
            else:
                logger.info("[fishing] %s no fridge. Deciding directly.", account_id)
                final_msg_id = fishing_msg_id

            # 5. Final Decision: Sell or Feed
            msg = await self._fetch_msg(client, target_group, final_msg_id)
            if not msg:
                return False

            food_val = self._parse_food_value(msg.message)
            if food_val is None:
                logger.warning("[fishing] %s could not parse food value. Defaulting to sell.", account_id)
                food_val = 999  # Fallback to sell

            action = self._decide_action(food_val, current_hunger, max_hunger)
            logger.info("[fishing] %s decided to %s (Food: %d, Hunger: %d/%d)", account_id, action, food_val, current_hunger, max_hunger)

            if not await self._robust_click(client, target_group, final_msg_id, action):
                logger.warning("[fishing] %s failed to click final action button.", account_id)
                return False

            logger.info("[fishing] %s fishing cycle complete.", account_id)
            return True

        except NoAvailableChat:
            raise
        except FloodWaitError as e:
            wait = getattr(e, 'seconds', 60)
            logger.warning("[fishing] %s FloodWait %ss during fishing. Sleeping.", account_id, wait)
            await asyncio.sleep(wait + 5)
            return False
        except Exception as e:
            logger.exception("[fishing] %s unexpected error during fishing: %s", account_id, e)
            return False

    # ------------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------------
    def _parse_hunger(self, text: str) -> tuple[int, int]:
        try:
            clean_text = text.replace("`", "")
            match = re.search(r"شکم\s*:.*\((\d+)\s*/\s*(\d+)\)", clean_text)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception:
            pass
        return 0, 0

    def _parse_food_value(self, text: str) -> int | None:
        try:
            clean_text = text.replace("`", "")
            match = re.search(r"ارزش غذایی\s*:\s*(\d+)", clean_text)
            if match:
                return int(match.group(1))
        except Exception:
            pass
        return None

    def _parse_cook_time(self, text: str) -> int:
        try:
            match = re.search(r"زمان مورد نیاز پخیدن\s*:\s*(\d+):(\d+)", text)
            if match:
                mins, secs = int(match.group(1)), int(match.group(2))
                return (mins * 60) + secs + 10  # +10s buffer
        except Exception:
            pass
        return 70  # Fallback 60s + 10s buffer

    def _decide_action(self, food_val: int, current_hunger: int, max_hunger: int) -> str:
        if food_val > 6:
            return "فروش ماهی"
        
        remaining_space = max_hunger - current_hunger
        if remaining_space <= 0:
            return "فروش ماهی"
            
        if food_val <= remaining_space:
            return "بده پیشی"
        else:
            return "فروش ماهی"

    async def _fetch_msg(self, client, group_conf, msg_id):
        try:
            messages = await client.get_messages(group_conf["id"], ids=msg_id)
            return messages[0] if isinstance(messages, list) else messages
        except Exception:
            return None

    async def _wait_for_buttons(self, client, group_conf, msg_id, timeout=150) -> bool:
        for _ in range(timeout // 5):
            msg = await self._fetch_msg(client, group_conf, msg_id)
            if msg:
                buttons = await msg.get_buttons()
                if buttons:
                    return True
            await asyncio.sleep(5)
        return False

    async def _robust_click(self, client, group_conf, msg_id, match_text: str) -> bool:
        """Clicks a button and verifies if the message was edited as a result."""
        for attempt in range(30):  # Max 150 seconds
            msg = await self._fetch_msg(client, group_conf, msg_id)
            if not msg:
                await asyncio.sleep(5)
                continue

            old_text = msg.message
            old_edit_date = msg.edit_date

            buttons = await msg.get_buttons()
            if not buttons:
                await asyncio.sleep(5)
                continue

            clicked = False
            for row in buttons:
                for btn in row:
                    if match_text in btn.text:
                        try:
                            await msg.click(text=btn.text)
                            clicked = True
                            logger.info("[fishing] Clicked '%s' (attempt %d). Verifying edit...", match_text, attempt + 1)
                        except Exception as e:
                            logger.warning("[fishing] Click exception on '%s': %s. Retrying...", match_text, e)
                        break
                if clicked:
                    break

            if clicked:
                await asyncio.sleep(3)  # wait for edit
                verify_msg = await self._fetch_msg(client, group_conf, msg_id)
                if verify_msg and (verify_msg.message != old_text or verify_msg.edit_date != old_edit_date):
                    logger.info("[fishing] Edit confirmed for '%s'.", match_text)
                    return True
                else:
                    logger.warning("[fishing] Click on '%s' did not trigger edit. Retrying...", match_text)
            await asyncio.sleep(5)
            
        logger.error("[fishing] Failed to robustly click '%s' after 30 attempts.", match_text)
        return False

    async def _click_first_non_upgrade(self, client, group_conf, msg_id) -> bool:
        """Clicks the first button that doesn't contain 'ارتقا' (upgrade)."""
        for attempt in range(30):
            msg = await self._fetch_msg(client, group_conf, msg_id)
            if not msg:
                await asyncio.sleep(5)
                continue

            old_text = msg.message
            old_edit_date = msg.edit_date

            buttons = await msg.get_buttons()
            if not buttons:
                await asyncio.sleep(5)
                continue

            clicked = False
            for row in buttons:
                for btn in row:
                    if "ارتقا" not in btn.text:
                        try:
                            await msg.click(text=btn.text)
                            clicked = True
                            logger.info("[fishing] Clicked non-upgrade fish button (attempt %d). Verifying edit...", attempt + 1)
                        except Exception as e:
                            logger.warning("[fishing] Click exception on fish: %s. Retrying...", e)
                        break
                if clicked:
                    break

            if clicked:
                await asyncio.sleep(3)
                verify_msg = await self._fetch_msg(client, group_conf, msg_id)
                if verify_msg and (verify_msg.message != old_text or verify_msg.edit_date != old_edit_date):
                    logger.info("[fishing] Edit confirmed for fish selection.")
                    return True
                else:
                    logger.warning("[fishing] Click on fish did not trigger edit. Retrying...")
            await asyncio.sleep(5)

        logger.error("[fishing] Failed to click fish button after 30 attempts.")
        return False

    async def _click_confirm(self, client, group_conf, msg_id) -> bool:
        """Clicks the leftmost button (confirm tick) and verifies edit."""
        for attempt in range(30):
            msg = await self._fetch_msg(client, group_conf, msg_id)
            if not msg:
                await asyncio.sleep(5)
                continue

            old_text = msg.message
            old_edit_date = msg.edit_date

            buttons = await msg.get_buttons()
            if not buttons:
                await asyncio.sleep(5)
                continue

            try:
                # Click the leftmost button
                await buttons[0][0].click()
                logger.info("[fishing] Clicked confirm button (attempt %d). Verifying edit...", attempt + 1)
            except Exception as e:
                logger.warning("[fishing] Confirm click exception: %s. Retrying...", e)
                await asyncio.sleep(5)
                continue

            await asyncio.sleep(3)
            verify_msg = await self._fetch_msg(client, group_conf, msg_id)
            if verify_msg and (verify_msg.message != old_text or verify_msg.edit_date != old_edit_date):
                logger.info("[fishing] Edit confirmed for confirm button.")
                return True
            else:
                logger.warning("[fishing] Click on confirm did not trigger edit. Retrying...")
            await asyncio.sleep(5)

        logger.error("[fishing] Failed to click confirm button after 30 attempts.")
        return False
