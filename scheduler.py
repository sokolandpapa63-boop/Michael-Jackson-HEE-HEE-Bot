from datetime import datetime
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def check_reminders(bot: Bot):
    tasks = await db.get_upcoming_tasks()
    for tid, uid, title, deadline in tasks:
        try:
            await bot.send_message(
                uid,
                f"⏰ **Напоминание!**\n\nЗадача: **{title}**\nДедлайн: {deadline}\n\nУспей до конца! 💪",
                parse_mode="Markdown",
            )
            await db.mark_reminded(tid)
        except Exception as e:
            print(f"Reminder error: {e}")


async def daily_summary(bot: Bot):
    now = datetime.now().strftime("%H:%M")
    users = await db.get_users_for_summary(now)
    for uid in users:
        tasks = await db.get_tasks(uid, "today")
        if not tasks:
            continue
        text = "☀️ **Доброе утро!** Твои задачи на сегодня:\n\n"
        for t in tasks:
            tid, _, title, deadline, prio, _ = t
            emoji = {1: "🔴", 2: "🟡", 3: "🟢"}.get(prio, "⚪")
            text += f"{emoji} {title}\n"
        try:
            await bot.send_message(uid, text, parse_mode="Markdown")
        except Exception as e:
            print(f"Summary error: {e}")


def setup_scheduler(bot: Bot):
    scheduler.add_job(check_reminders, "interval", minutes=5, args=[bot])
    scheduler.add_job(daily_summary, "interval", minutes=1, args=[bot])
    scheduler.start()
