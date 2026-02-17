from __future__ import annotations

from typing import Literal

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class ConfirmCb(CallbackData, prefix="confirm"):
    action: Literal["apply", "cancel", "back"]


def confirm_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Применить в таблицу", callback_data=ConfirmCb(action="apply").pack())
    kb.button(text="❌ Отмена", callback_data=ConfirmCb(action="cancel").pack())
    kb.adjust(1)
    return kb.as_markup()


def back_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data=ConfirmCb(action="back").pack())
    kb.adjust(1)
    return kb.as_markup()
