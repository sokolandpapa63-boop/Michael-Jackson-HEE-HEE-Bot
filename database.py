import aiosqlite
from datetime import datetime
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            daily_summary_time TEXT DEFAULT '09:00'
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            description TEXT,
            deadline TEXT,
            created_at TEXT,
            done INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            goal_id INTEGER,
            title TEXT,
            deadline TEXT,
            priority INTEGER DEFAULT 2,
            done INTEGER DEFAULT 0,
            created_at TEXT,
            reminded INTEGER DEFAULT 0
        );
        """)
        await db.commit()


async def add_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )
        await db.commit()


# ---------- GOALS ----------
async def add_goal(user_id, title, description, deadline):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO goals (user_id, title, description, deadline, created_at) VALUES (?,?,?,?,?)",
            (user_id, title, description, deadline, datetime.now().isoformat()),
        )
        await db.commit()
        return cur.lastrowid


async def get_goals(user_id, only_active=True):
    async with aiosqlite.connect(DB_PATH) as db:
        q = "SELECT id, title, description, deadline, done FROM goals WHERE user_id=?"
        if only_active:
            q += " AND done=0"
        cur = await db.execute(q, (user_id,))
        return await cur.fetchall()


async def get_goal(goal_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, user_id, title, description, deadline, done FROM goals WHERE id=?",
            (goal_id,),
        )
        return await cur.fetchone()


async def complete_goal(goal_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE goals SET done=1 WHERE id=?", (goal_id,))
        await db.commit()


async def delete_goal(goal_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM goals WHERE id=?", (goal_id,))
        await db.execute("UPDATE tasks SET goal_id=NULL WHERE goal_id=?", (goal_id,))
        await db.commit()


async def goal_progress(goal_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM tasks WHERE goal_id=?", (goal_id,))
        total = (await cur.fetchone())[0]
        cur = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE goal_id=? AND done=1", (goal_id,)
        )
        done = (await cur.fetchone())[0]
        return done, total


# ---------- TASKS ----------
async def add_task(user_id, title, deadline, priority, goal_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO tasks (user_id, goal_id, title, deadline, priority, created_at) VALUES (?,?,?,?,?,?)",
            (user_id, goal_id, title, deadline, priority, datetime.now().isoformat()),
        )
        await db.commit()
        return cur.lastrowid


async def get_tasks(user_id, filter_type="all"):
    async with aiosqlite.connect(DB_PATH) as db:
        q = "SELECT id, goal_id, title, deadline, priority, done FROM tasks WHERE user_id=?"
        params = [user_id]
        if filter_type == "today":
            q += " AND date(deadline)=date('now') AND done=0"
        elif filter_type == "week":
            q += " AND date(deadline) BETWEEN date('now') AND date('now','+7 day') AND done=0"
        elif filter_type == "active":
            q += " AND done=0"
        q += " ORDER BY priority ASC, deadline ASC"
        cur = await db.execute(q, params)
        return await cur.fetchall()


async def complete_task(task_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
        await db.commit()


async def delete_task(task_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        await db.commit()


async def get_task(task_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, user_id, goal_id, title, deadline, priority, done FROM tasks WHERE id=?",
            (task_id,),
        )
        return await cur.fetchone()


async def get_upcoming_tasks():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, user_id, title, deadline FROM tasks
            WHERE done=0 AND reminded=0
              AND datetime(deadline) BETWEEN datetime('now') AND datetime('now','+1 hour')
        """)
        return await cur.fetchall()


async def mark_reminded(task_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET reminded=1 WHERE id=?", (task_id,))
        await db.commit()


async def get_users_for_summary(current_time):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id FROM users WHERE daily_summary_time=?", (current_time,)
        )
        return [r[0] for r in await cur.fetchall()]


# ---------- STATS ----------
async def get_stats(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=? AND done=1 AND date(created_at) >= date('now','-7 day')",
            (user_id,),
        )
        week_done = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=? AND done=1 AND date(created_at) >= date('now','-30 day')",
            (user_id,),
        )
        month_done = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=? AND done=0", (user_id,)
        )
        active = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COUNT(*) FROM goals WHERE user_id=? AND done=0", (user_id,)
        )
        goals_active = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COUNT(*) FROM goals WHERE user_id=? AND done=1", (user_id,)
        )
        goals_done = (await cur.fetchone())[0]

        return {
            "week_done": week_done,
            "month_done": month_done,
            "active": active,
            "goals_active": goals_active,
            "goals_done": goals_done,
        }
