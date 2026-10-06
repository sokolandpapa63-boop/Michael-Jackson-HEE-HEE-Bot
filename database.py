import asyncpg
from datetime import datetime
from config import DATABASE_URL

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            daily_summary_time TEXT DEFAULT '09:00'
        );

        CREATE TABLE IF NOT EXISTS goals (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            title TEXT,
            description TEXT,
            deadline TEXT,
            created_at TEXT,
            done INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            goal_id INTEGER,
            title TEXT,
            deadline TEXT,
            priority INTEGER DEFAULT 2,
            done INTEGER DEFAULT 0,
            created_at TEXT,
            reminded INTEGER DEFAULT 0
        );
        """)


async def add_user(user_id: int, username: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
            user_id, username or "",
        )


# ---------- GOALS ----------
async def add_goal(user_id, title, description, deadline):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO goals (user_id, title, description, deadline, created_at) VALUES ($1,$2,$3,$4,$5) RETURNING id",
            user_id, title, description, deadline, datetime.now().isoformat(),
        )
        return row["id"]


async def get_goals(user_id, only_active=True):
    pool = await get_pool()
    async with pool.acquire() as conn:
        q = "SELECT id, title, description, deadline, done FROM goals WHERE user_id=$1"
        if only_active:
            q += " AND done=0"
        rows = await conn.fetch(q, user_id)
        return [tuple(r) for r in rows]


async def get_goal(goal_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id, title, description, deadline, done FROM goals WHERE id=$1",
            goal_id,
        )
        return tuple(row) if row else None


async def complete_goal(goal_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE goals SET done=1 WHERE id=$1", goal_id)


async def delete_goal(goal_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM goals WHERE id=$1", goal_id)
        await conn.execute("UPDATE tasks SET goal_id=NULL WHERE goal_id=$1", goal_id)


async def goal_progress(goal_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM tasks WHERE goal_id=$1", goal_id)
        done = await conn.fetchval("SELECT COUNT(*) FROM tasks WHERE goal_id=$1 AND done=1", goal_id)
        return done, total


# ---------- TASKS ----------
async def add_task(user_id, title, deadline, priority, goal_id=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO tasks (user_id, goal_id, title, deadline, priority, created_at) VALUES ($1,$2,$3,$4,$5,$6) RETURNING id",
            user_id, goal_id, title, deadline, priority, datetime.now().isoformat(),
        )
        return row["id"]


async def get_tasks(user_id, filter_type="all"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        q = "SELECT id, goal_id, title, deadline, priority, done FROM tasks WHERE user_id=$1"
        if filter_type == "today":
            q += " AND deadline::date = CURRENT_DATE AND done=0"
        elif filter_type == "week":
            q += " AND deadline::date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 day' AND done=0"
        elif filter_type == "active":
            q += " AND done=0"
        q += " ORDER BY priority ASC, deadline ASC NULLS LAST"
        rows = await conn.fetch(q, user_id)
        return [tuple(r) for r in rows]


async def complete_task(task_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE tasks SET done=1 WHERE id=$1", task_id)


async def delete_task(task_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM tasks WHERE id=$1", task_id)


async def get_task(task_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id, goal_id, title, deadline, priority, done FROM tasks WHERE id=$1",
            task_id,
        )
        return tuple(row) if row else None


async def get_upcoming_tasks():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, user_id, title, deadline FROM tasks
            WHERE done=0 AND reminded=0
              AND deadline IS NOT NULL
              AND deadline::timestamp BETWEEN NOW() AND NOW() + INTERVAL '1 hour'
        """)
        return [tuple(r) for r in rows]


async def mark_reminded(task_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE tasks SET reminded=1 WHERE id=$1", task_id)


async def get_users_for_summary(current_time):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id FROM users WHERE daily_summary_time=$1", current_time
        )
        return [r["user_id"] for r in rows]


# ---------- STATS ----------
async def get_stats(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        week_done = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE user_id=$1 AND done=1 AND created_at::timestamp >= NOW() - INTERVAL '7 day'",
            user_id,
        )
        month_done = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE user_id=$1 AND done=1 AND created_at::timestamp >= NOW() - INTERVAL '30 day'",
            user_id,
        )
        active = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE user_id=$1 AND done=0", user_id
        )
        goals_active = await conn.fetchval(
            "SELECT COUNT(*) FROM goals WHERE user_id=$1 AND done=0", user_id
        )
        goals_done = await conn.fetchval(
            "SELECT COUNT(*) FROM goals WHERE user_id=$1 AND done=1", user_id
        )
        return {
            "week_done": week_done,
            "month_done": month_done,
            "active": active,
            "goals_active": goals_active,
            "goals_done": goals_done,
        }
