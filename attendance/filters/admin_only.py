from __future__ import annotations

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message, User

from ..config import Settings


class AdminOnly(Filter):
    async def __call__(
        self,
        event: Message | CallbackQuery,
        event_from_user: User | None,
        settings: Settings,
    ) -> bool:
        if event_from_user is None:
            return False

        if settings.admin_ids is None or event_from_user.id in settings.admin_ids:
            return True

        if isinstance(event, Message):
            await event.answer("Нет доступа.")
        else:
            await event.answer("Нет доступа.", show_alert=True)
        return False
