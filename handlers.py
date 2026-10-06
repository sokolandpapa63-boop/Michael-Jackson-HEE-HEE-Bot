from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import (
    main_menu, tasks_menu, goals_menu, priority_kb,
    goals_choice_kb, task_actions_kb, goal_actions_kb, back_kb,
)

router = Router()


class TaskFSM(StatesGroup):
    title = State()
    deadline = State()
    priority = State()
    goal = State()


class GoalFSM(StatesGroup):
    title = State()
    description = State()
    deadline = State()


PRIO_EMOJI = {1: "🔴", 2: "🟡", 3: "🟢"}


# ---------- /start ----------
@router.message(Command("start"))
async def cmd_start(message: Message):
    await db.add_user(message.from_user.id, message.from_user.username or "")
    await message.answer(
        f"Привет, {message.from_user.first_name}! 🍬\n\n"
        "Я твой личный **TaskMaster** — помогу планировать задачи и достигать целей!\n\n"
        "Выбирай, с чего начнём 👇",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "Главное меню 👇", reply_markup=main_menu()
    )


# ---------- ЗАДАЧИ ----------
@router.callback_query(F.data == "menu_tasks")
async def menu_tasks(call: CallbackQuery):
    await call.message.edit_text("📝 Раздел задач:", reply_markup=tasks_menu())


@router.callback_query(F.data == "task_add")
async def task_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(TaskFSM.title)
    await call.message.edit_text("✏️ Введи название задачи:", reply_markup=back_kb())


@router.message(TaskFSM.title)
async def task_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(TaskFSM.deadline)
    await message.answer(
        "📅 Когда дедлайн? Напиши в формате:\n`YYYY-MM-DD HH:MM`\n"
        "Например: `2026-12-31 18:00`\n\n"
        "Или отправь `-` чтобы без дедлайна.",
        parse_mode="Markdown",
    )


@router.message(TaskFSM.deadline)
async def task_deadline(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        deadline = None
    else:
        try:
            datetime.strptime(text, "%Y-%m-%d %H:%M")
            deadline = text
        except ValueError:
            await message.answer("❌ Неверный формат. Попробуй ещё раз: `YYYY-MM-DD HH:MM`", parse_mode="Markdown")
            return
    await state.update_data(deadline=deadline)
    await state.set_state(TaskFSM.priority)
    await message.answer("Выбери приоритет:", reply_markup=priority_kb())


@router.callback_query(TaskFSM.priority, F.data.startswith("prio_"))
async def task_priority(call: CallbackQuery, state: FSMContext):
    prio = int(call.data.split("_")[1])
    await state.update_data(priority=prio)

    goals = await db.get_goals(call.from_user.id)
    if goals:
        await state.set_state(TaskFSM.goal)
        await call.message.edit_text(
            "🎯 Привязать к цели?", reply_markup=goals_choice_kb(goals)
        )
    else:
        data = await state.get_data()
        await db.add_task(
            call.from_user.id, data["title"], data["deadline"], data["priority"], None
        )
        await state.clear()
        await call.message.edit_text("✅ Задача добавлена!", reply_markup=tasks_menu())


@router.callback_query(TaskFSM.goal, F.data.startswith("setgoal_"))
async def task_goal(call: CallbackQuery, state: FSMContext):
    goal_id = int(call.data.split("_")[1]) or None
    data = await state.get_data()
    await db.add_task(
        call.from_user.id, data["title"], data["deadline"], data["priority"], goal_id
    )
    await state.clear()
    await call.message.edit_text("✅ Задача добавлена!", reply_markup=tasks_menu())


@router.callback_query(F.data.startswith("task_list_"))
async def task_list(call: CallbackQuery):
    flt = call.data.replace("task_list_", "")
    tasks = await db.get_tasks(call.from_user.id, flt)

    if not tasks:
        await call.message.edit_text("😴 Тут пусто.", reply_markup=tasks_menu())
        return

    titles = {"active": "📋 Активные задачи", "today": "📅 Задачи на сегодня", "week": "🗓 Задачи на неделю"}
    text = f"**{titles.get(flt, 'Задачи')}:**\n\n"
    for t in tasks:
        tid, goal_id, title, deadline, prio, done = t
        line = f"{PRIO_EMOJI.get(prio, '⚪')} {title}"
        if deadline:
            line += f"\n   ⏰ {deadline}"
        text += line + "\n\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    for t in tasks:
        tid, _, title, _, _, _ = t
        kb.button(text=f"⚙️ {title[:30]}", callback_data=f"tinfo_{tid}")
    kb.button(text="⬅️ Назад", callback_data="menu_tasks")
    kb.adjust(1)

    await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data.startswith("tinfo_"))
async def task_info(call: CallbackQuery):
    tid = int(call.data.split("_")[1])
    t = await db.get_task(tid)
    if not t:
        await call.answer("Задача не найдена", show_alert=True)
        return
    _, _, goal_id, title, deadline, prio, done = t
    text = f"**{title}**\n{PRIO_EMOJI.get(prio,'⚪')} Приоритет: {prio}\n"
    if deadline:
        text += f"⏰ Дедлайн: {deadline}\n"
    text += f"Статус: {'✅ выполнено' if done else '🔄 в работе'}"
    await call.message.edit_text(text, reply_markup=task_actions_kb(tid), parse_mode="Markdown")


@router.callback_query(F.data.startswith("tdone_"))
async def task_done(call: CallbackQuery):
    tid = int(call.data.split("_")[1])
    await db.complete_task(tid)
    await call.answer("Красавчик! ✅")
    await call.message.edit_text("✅ Задача выполнена!", reply_markup=tasks_menu())


@router.callback_query(F.data.startswith("tdel_"))
async def task_del(call: CallbackQuery):
    tid = int(call.data.split("_")[1])
    await db.delete_task(tid)
    await call.answer("Удалено 🗑")
    await call.message.edit_text("🗑 Задача удалена.", reply_markup=tasks_menu())


# ---------- ЦЕЛИ ----------
@router.callback_query(F.data == "menu_goals")
async def menu_goals(call: CallbackQuery):
    await call.message.edit_text("🎯 Раздел целей:", reply_markup=goals_menu())


@router.callback_query(F.data == "goal_add")
async def goal_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(GoalFSM.title)
    await call.message.edit_text("🎯 Как называется цель?", reply_markup=back_kb())


@router.message(GoalFSM.title)
async def goal_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(GoalFSM.description)
    await message.answer("📝 Опиши цель (или отправь `-`):", parse_mode="Markdown")


@router.message(GoalFSM.description)
async def goal_desc(message: Message, state: FSMContext):
    desc = "" if message.text.strip() == "-" else message.text
    await state.update_data(description=desc)
    await state.set_state(GoalFSM.deadline)
    await message.answer("📅 Дедлайн цели? `YYYY-MM-DD` или `-`:", parse_mode="Markdown")


@router.message(GoalFSM.deadline)
async def goal_deadline(message: Message, state: FSMContext):
    text = message.text.strip()
    deadline = None if text == "-" else text
    if deadline:
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            await message.answer("❌ Формат: `YYYY-MM-DD`", parse_mode="Markdown")
            return
    data = await state.get_data()
    await db.add_goal(message.from_user.id, data["title"], data["description"], deadline)
    await state.clear()
    await message.answer("🎯 Цель добавлена! Теперь можешь привязать к ней задачи.", reply_markup=goals_menu())


@router.callback_query(F.data == "goal_list")
async def goal_list(call: CallbackQuery):
    goals = await db.get_goals(call.from_user.id)
    if not goals:
        await call.message.edit_text("😴 Целей пока нет.", reply_markup=goals_menu())
        return

    text = "**🎯 Твои цели:**\n\n"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    for g in goals:
        gid, title, desc, deadline, done = g
        d, total = await db.goal_progress(gid)
        pct = int(d / total * 100) if total else 0
        text += f"**{title}**\nПрогресс: {d}/{total} ({pct}%)\n"
        if deadline:
            text += f"⏰ {deadline}\n"
        text += "\n"
        kb.button(text=f"⚙️ {title[:30]}", callback_data=f"ginfo_{gid}")
    kb.button(text="⬅️ Назад", callback_data="menu_goals")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data.startswith("ginfo_"))
async def goal_info(call: CallbackQuery):
    gid = int(call.data.split("_")[1])
    g = await db.get_goal(gid)
    if not g:
        await call.answer("Цель не найдена", show_alert=True)
        return
    _, _, title, desc, deadline, done = g
    d, total = await db.goal_progress(gid)
    pct = int(d / total * 100) if total else 0
    text = f"**🎯 {title}**\n\n{desc or ''}\n\n"
    text += f"Прогресс: {d}/{total} ({pct}%)"
    if deadline:
        text += f"\n⏰ Дедлайн: {deadline}"
    await call.message.edit_text(text, reply_markup=goal_actions_kb(gid), parse_mode="Markdown")


@router.callback_query(F.data.startswith("gdone_"))
async def goal_done(call: CallbackQuery):
    gid = int(call.data.split("_")[1])
    await db.complete_goal(gid)
    await call.answer("Цель достигнута! 🎉")
    await call.message.edit_text("🎉 Поздравляю с достижением цели!", reply_markup=goals_menu())


@router.callback_query(F.data.startswith("gdel_"))
async def goal_del(call: CallbackQuery):
    gid = int(call.data.split("_")[1])
    await db.delete_goal(gid)
    await call.answer("Удалено")
    await call.message.edit_text("🗑 Цель удалена.", reply_markup=goals_menu())


# ---------- СТАТИСТИКА ----------
@router.callback_query(F.data == "menu_stats")
async def menu_stats(call: CallbackQuery):
    s = await db.get_stats(call.from_user.id)
    text = (
        "**📊 Твоя статистика:**\n\n"
        f"✅ Выполнено за неделю: **{s['week_done']}**\n"
        f"✅ Выполнено за месяц: **{s['month_done']}**\n"
        f"🔄 Активных задач: **{s['active']}**\n"
        f"🎯 Активных целей: **{s['goals_active']}**\n"
        f"🏆 Достигнуто целей: **{s['goals_done']}**"
    )
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")


@router.callback_query(F.data == "menu_settings")
async def menu_settings(call: CallbackQuery):
    await call.message.edit_text(
        "⏰ Напоминания о задачах приходят автоматически за час до дедлайна.\n"
        "Ежедневная сводка — каждое утро в 9:00.\n\n"
        "(Изменение времени можно добавить позже 😉)",
        reply_markup=back_kb(),
    )