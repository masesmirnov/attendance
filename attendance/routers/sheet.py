from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..repositories.user_sheets import SQLiteUserSheetRepository
from ..states import Flow
from ..utils.validation import extract_sheet_id

router = Router(name=__name__)


@router.message(Command("sheet"))
async def cmd_sheet(message: Message, state: FSMContext, user_sheets: SQLiteUserSheetRepository) -> None:
    assert message.from_user is not None
    user_id = message.from_user.id

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) == 2:
        sheet_id = extract_sheet_id(parts[1])
        if not sheet_id:
            await message.answer("Не похоже на Spreadsheet ID или ссылку Google Sheets. Пришли ID из /d/.../edit.")
            return

        await user_sheets.set_sheet_id(user_id, sheet_id)
        await state.clear()
        await state.set_state(Flow.waiting_image)
        await message.answer("✅ Сохранил ID таблицы.\nТеперь пришли скриншот с присутствующими.")
        return

    current = await user_sheets.get_sheet_id(user_id)
    await state.set_state(Flow.waiting_sheet_id)
    await message.answer(
        "Пришли новый <b>Spreadsheet ID</b> (можно ссылкой).\n"
        f"Текущий (персональный): <code>{html.escape(current) if current else '— не задан —'}</code>\n\n"
        "Можно также: /sheet <code>&lt;ID&gt;</code>"
    )


@router.message(Flow.waiting_sheet_id, F.text)
async def handle_sheet_id(message: Message, state: FSMContext, user_sheets: SQLiteUserSheetRepository) -> None:
    assert message.from_user is not None
    user_id = message.from_user.id

    sheet_id = extract_sheet_id(message.text or "")
    if not sheet_id:
        await message.answer("Не похоже на Spreadsheet ID или ссылку Google Sheets. Пришли ID из /d/.../edit.")
        return

    await user_sheets.set_sheet_id(user_id, sheet_id)
    await state.clear()
    await state.set_state(Flow.waiting_image)
    await message.answer("✅ Сохранил ID таблицы.\nТеперь пришли скриншот с присутствующими.")
