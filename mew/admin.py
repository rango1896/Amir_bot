"""
Admin commands bridging the core userbot to MewManager.

Commands (admin-only, registered on every client just like !ping):
  !mew add <user>      add an account to the mew cycle (by session_name or JSON key)
  !mew remove <user>   remove an account from the mew cycle
  !mew list            list added accounts with live task status
  !mewjoin <target>    mass-join all online mew accounts to a group/channel/invite link
"""
import asyncio
import re
import random
from telethon import events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import (
    UserAlreadyParticipantError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    ChannelsTooMuchError,
    FloodWaitError
)

# Reuse the admin check used everywhere else in the userbot.
ADMIN_IDS = [7821355283]


async def is_admin(event):
    return event.sender_id in ADMIN_IDS


def register_mew_commands(client, mew_manager):
    @client.on(events.NewMessage(pattern=r"^!mew\s+add\s+(\S+)", outgoing=True))
    async def _mew_add(event):
        if not await is_admin(event):
            return
        identifier = event.pattern_match.group(1).strip()
        ok, msg = await mew_manager.add_user(identifier)
        await event.reply(msg)

    @client.on(events.NewMessage(pattern=r"^!mew\s+remove\s+(\S+)", outgoing=True))
    async def _mew_remove(event):
        if not await is_admin(event):
            return
        identifier = event.pattern_match.group(1).strip()
        ok, msg = await mew_manager.remove_user(identifier)
        await event.reply(msg)

    @client.on(events.NewMessage(pattern=r"^!mew\s+list(?:\s|$)", outgoing=True))
    async def _mew_list(event):
        if not await is_admin(event):
            return
        users = await mew_manager.list_users()
        if not users:
            await event.reply("📭 **Mew cycle is empty.**\nUse `!mew add <user>` to add one.")
            return

        lines = [f"🐾 **Mew Cycle — {len(users)} account(s):**\n"]
        for u in users:
            status_icon = "🟢" if u["online"] else "🔴"
            line = f"{status_icon} `{u['account_id']}` (`{u['session_name']}`)"
            task_parts = []
            for tname, running in u["tasks"].items():
                task_parts.append(f"{tname}={'on' if running else 'off'}")
            if task_parts:
                line += f"  [{', '.join(task_parts)}]"
            lines.append(line)

        await event.reply("\n".join(lines))

    # -----------------------------------------------------------------
    # NEW: MASS JOIN COMMAND FOR MEW USERS
    # -----------------------------------------------------------------
    @client.on(events.NewMessage(pattern=r"^!mewjoin\s+(\S+)", outgoing=True))
    async def _mew_join(event):
        if not await is_admin(event):
            return
            
        if not event.is_private:
            return

        chat_target = event.pattern_match.group(1).strip()
        users = await mew_manager.list_users()
        
        online_mews = [u for u in users if u.get("online")]
        
        if not online_mews:
            await event.reply("❌ **Mass Join Aborted:** There are no active or online Mew sessions currently running.")
            return

        status_msg = await event.reply(
            f"🚀 **Mew Mass Join Initiated**\n"
            f"🎯 **Target Chat:** `{chat_target}`\n"
            f"👥 **Total Online Mews:** `{len(online_mews)}` accounts\n"
            f"_Processing sequence with anti-flood protections..._"
        )

        success_count = 0
        fail_count = 0
        log_lines = []

        for idx, u in enumerate(online_mews):
            account_id = u["account_id"]
            
            # --- THE FIX IS HERE ---
            # MewManager already holds a reference to AccountManager, 
            # so we just use it to reach into the live accounts dictionary.
            user_client = None
            if account_id in mew_manager.account_manager.accounts:
                user_client = mew_manager.account_manager.accounts[account_id].get('client')

            if not user_client or not user_client.is_connected():
                log_lines.append(f"🔴 `{account_id}`: Skipped (Session connection offline)")
                fail_count += 1
                continue

            try:
                # Execution Pattern A: Private Invite Links (t.me/+hash or t.me/joinchat/hash)
                if "t.me/+" in chat_target or "t.me/joinchat/" in chat_target:
                    invite_hash = chat_target.split("/+")[-1].split("?")[0] if "t.me/+" in chat_target else chat_target.split("/joinchat/")[-1].split("?")[0]
                    await user_client(ImportChatInviteRequest(invite_hash))
                
                # Execution Pattern B: Public Usernames/Links
                else:
                    clean_chat = chat_target.replace("https://t.me/", "").replace("http://t.me/", "").replace("t.me/", "").lstrip("@")
                    clean_chat = clean_chat.split("/")[0].split("?")[0]
                    await user_client(JoinChannelRequest(clean_chat))

                log_lines.append(f"🟢 `{account_id}`: Successfully joined target")
                success_count += 1

            except UserAlreadyParticipantError:
                log_lines.append(f"ℹ️ `{account_id}`: Already a member")
                success_count += 1
            except InviteHashExpiredError:
                log_lines.append(f"❌ `{account_id}`: Expired invite link")
                fail_count += 1
            except InviteHashInvalidError:
                log_lines.append(f"❌ `{account_id}`: Invalid invite link")
                fail_count += 1
            except ChannelsTooMuchError:
                log_lines.append(f"❌ `{account_id}`: Max channel limit reached")
                fail_count += 1
            except FloodWaitError as e:
                log_lines.append(f"⏳ `{account_id}`: Hit FloodWait ({e.seconds}s)")
                fail_count += 1
                # If a structural floodwait occurs, extend the buffer block to preserve the session
                await asyncio.sleep(e.seconds + 2)
            except Exception as e:
                log_lines.append(f"❌ `{account_id}`: Failed ({type(e).__name__})")
                fail_count += 1

            # Dynamic status summary push to keep the log interactive
            if (idx + 1) % 3 == 0 or (idx + 1) == len(online_mews):
                progress_text = (
                    f"⏳ **Mew Mass Join Processing... ({idx + 1}/{len(online_mews)})**\n\n"
                    f"{'\n'.join(log_lines[-8:])}\n\n"
                    f"🟢 Success: `{success_count}` | 🔴 Failed: `{fail_count}`"
                )
                try:
                    await status_msg.edit(progress_text)
                except Exception:
                    pass

            # Anti-Spam Jitter: Only sleep if there are more iterations remaining
            if idx < len(online_mews) - 1:
                delay = random.uniform(6.5, 14.5)
                await asyncio.sleep(delay)

        # Final Summary Presentation
        final_report = (
            f"✅ **Mew Mass Join Completed!**\n\n"
            f"📊 **Final Statistics:**\n"
            f"  └ 🟢 Successful Actions: `{success_count}`\n"
            f"  └ 🔴 Failed Actions: `{fail_count}`\n"
            f"  └ Total Swept Sessions: `{len(online_mews)}` accounts\n\n"
            f"📋 **Full Operations Log:**\n" + "\n".join(log_lines)
        )
        
        if len(final_report) > 4000:
            final_report = final_report[:3900] + "\n\n⚠️ _Log output truncated due to layout size limitations._"
            
        await status_msg.edit(final_report)


    # Usage: 
    #   !mew fishing off          (turns off fishing for the sender)
    #   !mew fishing on tiramiso     (admin turns on fishing for tiramiso)
    @client.on(events.NewMessage(pattern=r"^!mew\s+(auto_mew|fishing|collect)\s+(on|off)(?:\s+(\S+))?", outgoing=True))
    async def _mew_toggle_task(event):
        task_name = event.pattern_match.group(1)
        action = event.pattern_match.group(2)
        identifier = event.pattern_match.group(3)
        
        enabled = (action == "on")
        
        if identifier:
            # If an account is specified, require admin rights
            if not await is_admin(event):
                return
                
            match_id = None
            for acc_id, cfg in mew_manager.account_manager.all_configs.items():
                if acc_id == identifier or cfg.get("session_name") == identifier:
                    match_id = acc_id
                    break
            
            if not match_id:
                # Check if it's a raw account_id in the DB
                added = await mew_manager.db.list_added()
                for acc_id, _ in added:
                    if acc_id == identifier:
                        match_id = acc_id
                        break
                
            if not match_id:
                await event.reply(f"❌ Account `{identifier}` not found.")
                return
                
            target_acc = match_id
        else:
            # Self-target (the session turning off its own task)
            target_acc = event.client.account_id
            
        ok, msg = await mew_manager.set_task_state(target_acc, task_name, enabled)
        await event.reply(msg)