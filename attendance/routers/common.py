from __future__ import annotations

import html

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..config import Settings
from ..repositories.user_sheets import SQLiteUserSheetRepository
from ..states import Flow

router = Router(name=__name__)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    settings: Settings,
    user_sheets: SQLiteUserSheetRepository,
) -> None:
    await state.clear()

    assert message.from_user is not None
    user_id = message.from_user.id

    sheet_id = await user_sheets.get_sheet_id(user_id) or settings.default_sheet_id
    if not sheet_id:
        await state.set_state(Flow.waiting_sheet_id)
        await message.answer(
            "Сначала пришли <b>ID таблицы Google Sheets</b> (из ссылки).\n"
            "Пример:\n"
            "<code>https://docs.google.com/spreadsheets/d/XXXXXXX/edit</code>\n"
            "Нужен кусок <code>XXXXXXX</code>.\n\n"
            "⚠️ Важно: добавь сервисный аккаунт в редакторы таблицы:\n"
            f"<code>{html.escape(settings.service_account_email)}</code>\n"
            "Google Sheets → Share → Add people → Editor\n\n"
            "Можно также: /sheet <code>&lt;ID&gt;</code>"
        )
        return

    await state.set_state(Flow.waiting_image)
    await message.answer(
        "Пришли скриншот, где видно присутствующих: участники созвона, чат, список — откуда угодно.\n"
        "Я верну JSON (имя → 0/1). Потом подтвердишь и укажешь колонку.\n\n"
        "Сменить таблицу: /sheet"
    )


@router.message(Command("help"))
async def cmd_help(message: Message, settings: Settings) -> None:
    await message.answer(
        "Как пользоваться:\n"
        "1) /start\n"
        "2) пришли скриншот с присутствующими (как фото или image-файл)\n"
        "3) получишь JSON\n"
        "4) нажми «Применить» и укажи колонку (например S или AA)\n\n"
        "/sheet — показать/сменить таблицу\n"
        "/sheet <code>&lt;ID&gt;</code> — быстро установить таблицу\n\n"
        "Доступ к таблице:\n"
        f"Добавьте в Editors: <code>{html.escape(settings.service_account_email)}</code>\n"
        "Google Sheets → Share → Editor\n\n"
        "/cancel — отмена"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Ок, отменил. /start чтобы начать заново.")
