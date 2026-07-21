# mew/tasks/base_task.py
import asyncio
import random
import logging
from telethon.errors import RPCError, FloodWaitError
from .. import config

logger = logging.getLogger("mew.tasks")


class NoAvailableChat(Exception):
    """Raised when every configured chat rejected sending the command."""


class BaseTask:
    name: str = "base"
    default_enabled: bool = False

    def __init__(self, mew_manager):
        self.mew_manager = mew_manager
        self.user_tasks: dict = {}

    async def loop(self, account_id: str, client):
        raise NotImplementedError

    async def _wrapped_loop(self, account_id: str, client):
        delay = random.uniform(0, config.MAX_STARTUP_DELAY)
        logger.info("[%s] %s startup delay: %.1fs", self.name, account_id, delay)
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise

        while True:
            try:
                await self.loop(account_id, client)
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception(
                    "[%s] loop for %s crashed: %s — backing off %ds",
                    self.name, account_id, e, config.CRASH_BACKOFF_SECONDS
                )
                try:
                    await asyncio.sleep(config.CRASH_BACKOFF_SECONDS)
                except asyncio.CancelledError:
                    raise

    async def ensure_running(self, account_id: str, client):
        existing = self.user_tasks.get(account_id)
        if existing:
            same_client = existing["client"] is client
            alive = not existing["task"].done()
            if same_client and alive:
                return
            await self.stop_for(account_id)

        task = asyncio.create_task(self._wrapped_loop(account_id, client))
        self.user_tasks[account_id] = {"task": task, "client": client}
        logger.info("[%s] started for %s", self.name, account_id)

    async def stop_for(self, account_id: str):
        entry = self.user_tasks.pop(account_id, None)
        if not entry:
            return
        task = entry["task"]
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("[%s] stopped for %s", self.name, account_id)

    async def stop_all(self):
        for account_id in list(self.user_tasks.keys()):
            await self.stop_for(account_id)

    def status(self) -> dict:
        return {
            acc_id: (not entry["task"].done())
            for acc_id, entry in self.user_tasks.items()
        }

    # ------------------------------------------------------------------
    # SHARED SEND-WITH-FAILOVER
    # ------------------------------------------------------------------
    async def _send_with_failover(self, client, text: str, account_id: str = ""):
        """
        Tries every configured group, in random order, until one accepts the
        message. Returns the group_config dictionary and the sent message.
        """
        candidates = list(config.GROUPS)
        random.shuffle(candidates)

        last_err = None
        for group_conf in candidates:
            group_id = group_conf["id"]
            try:
                sent_msg = await client.send_message(group_id, text)
                return group_conf, sent_msg
            except FloodWaitError:
                raise 
            except asyncio.CancelledError:
                raise
            except (RPCError, ValueError, TypeError) as e:
                last_err = e
                logger.warning(
                    "[%s] %s can't send to %s (%s: %s). Trying next chat...",
                    self.name, account_id, group_id, type(e).__name__, e
                )
                continue

        logger.error(
            "[%s] %s could not send to any configured chat (last error: %s). Dropping task.",
            self.name, account_id, last_err
        )
        raise NoAvailableChat(str(last_err))

    # ------------------------------------------------------------------
    # SHARED RETRY LOGIC FOR SUBCLASSES
    # ------------------------------------------------------------------
    async def _wait_for_bot_reply(self, client, target_group_conf, sent_msg_id):
        """
        Polls persistently for a reply from ANY of the bot mirrors to our sent message ID.
        Uses min_id to ONLY fetch messages newer than our command.
        """
        group_id = target_group_conf["id"]
        for attempt in range(config.REPLY_MAX_ATTEMPTS):
            async for msg in client.iter_messages(
                group_id, 
                min_id=sent_msg_id,
                limit=50  # Fetch last 50 messages to filter manually
            ):
                # Manually check if sender is one of the bot mirrors
                if msg.sender_id in config.MEOWIE_BOT_IDS:
                    if msg.reply_to and msg.reply_to.reply_to_msg_id == sent_msg_id:
                        return msg
            await asyncio.sleep(config.REPLY_POLL_INTERVAL)
        return None

    async def _wait_and_click_button(self, client, target_group_conf, reply_msg_id, required_texts: list[str]) -> bool:
        """
        Polls a specific message for a button and clicks it.
        Returns True immediately upon a successful click event.
        """
        group_id = target_group_conf["id"]
        for attempt in range(config.BUTTON_MAX_ATTEMPTS):
            try:
                messages = await client.get_messages(group_id, ids=reply_msg_id)
                msg = messages[0] if isinstance(messages, list) else messages

                if not msg:
                    await asyncio.sleep(config.BUTTON_POLL_INTERVAL)
                    continue

                buttons = await msg.get_buttons()
                if not buttons:
                    await asyncio.sleep(config.BUTTON_POLL_INTERVAL)
                    continue

                for row in buttons:
                    for btn in row:
                        if all(text in btn.text for text in required_texts):
                            try:
                                await msg.click(text=btn.text)
                                logger.info("[%s] Clicked button '%s' successfully.", self.name, btn.text)
                                return True
                            except Exception as click_err:
                                logger.warning("[%s] Click exception: %s. Will retry...", self.name, click_err)
                                break
                    else:
                        continue
                    break

            except RPCError as e:
                logger.warning("[%s] RPC error while checking button: %s", self.name, e)
            except Exception as e:
                logger.warning("[%s] Error checking message edits: %s", self.name, e)

            await asyncio.sleep(config.BUTTON_POLL_INTERVAL)

        return False
