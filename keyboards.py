from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Задачи", callback_data="menu_tasks")
    kb.button(text="🎯 Цели", callback_data="menu_goals")
    kb.button(text="📊 Статистика", callback_data="menu_stats")
    kb.button(text="⏰ Настройки", callback_data="menu_settings")
    kb.adjust(2, 2)
    return kb.as_markup()


def tasks_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить задачу", callback_data="task_add")
    kb.button(text="📋 Активные", callback_data="task_list_active")
    kb.button(text="📅 На сегодня", callback_data="task_list_today")
    kb.button(text="🗓 На неделю", callback_data="task_list_week")
    kb.button(text="⬅️ Назад", callback_data="back_main")
    kb.adjust(1, 3, 1)
    return kb.as_markup()


def goals_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить цель", callback_data="goal_add")
    kb.button(text="🎯 Мои цели", callback_data="goal_list")
    kb.button(text="⬅️ Назад", callback_data="back_main")
    kb.adjust(1, 1, 1)
    return kb.as_markup()


def priority_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔴 Высокий", callback_data="prio_1")
    kb.button(text="🟡 Средний", callback_data="prio_2")
    kb.button(text="🟢 Низкий", callback_data="prio_3")
    kb.adjust(3)
    return kb.as_markup()


def goals_choice_kb(goals):
    kb = InlineKeyboardBuilder()
    for g in goals:
        kb.button(text=f"🎯 {g[1][:30]}", callback_data=f"setgoal_{g[0]}")
    kb.button(text="🚫 Без цели", callback_data="setgoal_0")
    kb.button(text="⬅️ Отмена", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()


def task_actions_kb(task_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Выполнено", callback_data=f"tdone_{task_id}")
    kb.button(text="🗑 Удалить", callback_data=f"tdel_{task_id}")
    kb.button(text="⬅️ Назад", callback_data="back_main")
    kb.adjust(2, 1)
    return kb.as_markup()


def goal_actions_kb(goal_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Завершить", callback_data=f"gdone_{goal_id}")
    kb.button(text="🗑 Удалить", callback_data=f"gdel_{goal_id}")
    kb.button(text="⬅️ Назад", callback_data="back_main")
    kb.adjust(2, 1)
    return kb.as_markup()


def back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="back_main")
    return kb.as_markup()
