from __future__ import annotations

import html
import json
import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from ..config import Settings
from ..keyboards.confirm import ConfirmCb, back_keyboard, confirm_keyboard
from ..repositories.user_sheets import SQLiteUserSheetRepository
from ..services.google_sheets import GoogleSheetsService
from ..services.openai_attendance import AttendanceLLM
from ..states import Flow
from ..utils.render import as_html_json_codeblock
from ..utils.validation import is_valid_column, normalize_column

logger = logging.getLogger(__name__)
router = Router(name=__name__)


async def _effective_sheet_id(user_id: int, settings: Settings, user_sheets: SQLiteUserSheetRepository) -> str | None:
    return await user_sheets.get_sheet_id(user_id) or settings.default_sheet_id


async def _extract_image(message: Message, bot: Bot) -> tuple[bytes, str]:
    if message.photo:
        photo = message.photo[-1]
        buf = await bot.download(photo.file_id)
        return buf.getvalue(), "image/jpeg"

    doc = message.document
    if doc and doc.mime_type and doc.mime_type.startswith("image/"):
        buf = await bot.download(doc.file_id)
        return buf.getvalue(), doc.mime_type

    raise ValueError("Unsupported message: expected photo or image document")


async def _process_image(
    message: Message,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    user_sheets: SQLiteUserSheetRepository,
    sheets: GoogleSheetsService,
    attendance_llm: AttendanceLLM,
) -> None:
    assert message.from_user is not None
    user_id = message.from_user.id

    await message.answer("Ок, обрабатываю…")

    try:
        image_bytes, mime_type = await _extract_image(message, bot)
    except Exception:
        await message.answer("Пришли изображение (photo или image-файл).")
        return

    sheet_id = await _effective_sheet_id(user_id, settings, user_sheets)
    if not sheet_id:
        await state.clear()
        await state.set_state(Flow.waiting_sheet_id)
        await message.answer("Сначала задай таблицу: /sheet <code>ID</code>")
        return

    try:
        roster_entries = await sheets.get_roster(
            sheet_id,
            settings.worksheet_name,
            settings.roster_name_col,
            settings.roster_start_row,
        )
    except Exception as e:
        logger.exception("Failed to load roster from Google Sheets")
        await message.answer(f"Не смог прочитать реестр из таблицы: {html.escape(str(e))}")
        return

    if not roster_entries:
        await message.answer("Реестр пустой. Проверь WORKSHEET_NAME/ROSTER_NAME_COL/ROSTER_START_ROW.")
        return

    roster = [e.name for e in roster_entries]

    try:
        raw = await attendance_llm.analyze(roster, image_bytes, mime_type)
        simple = attendance_llm.marks_to_map(raw, roster)
    except Exception as e:
        logger.exception("OpenAI attendance analyze failed")
        await message.answer(f"Ошибка OpenAI: {html.escape(str(e))}")
        return

    await state.update_data(
        roster_entries=[{"row": e.row, "name": e.name} for e in roster_entries],
        simple=simple,
    )
    await state.set_state(Flow.waiting_confirm)

    json_txt = json.dumps(simple, ensure_ascii=False, indent=2)

    if len(json_txt) > 3500:
        f = BufferedInputFile(json_txt.encode("utf-8"), filename="attendance.json")
        await message.answer_document(
            document=f,
            caption="Готово. Итоговый JSON в файле.",
            reply_markup=confirm_keyboard(),
        )
        return

    await message.answer(
        "Готово. Итоговый JSON:\n" + as_html_json_codeblock(simple),
        reply_markup=confirm_keyboard(),
    )


@router.message(Flow.waiting_image, F.photo)
async def handle_photo(
    message: Message,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    user_sheets: SQLiteUserSheetRepository,
    sheets: GoogleSheetsService,
    attendance_llm: AttendanceLLM,
) -> None:
    await _process_image(message, state, bot, settings, user_sheets, sheets, attendance_llm)


@router.message(Flow.waiting_image, F.document)
async def handle_document_image(
    message: Message,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    user_sheets: SQLiteUserSheetRepository,
    sheets: GoogleSheetsService,
    attendance_llm: AttendanceLLM,
) -> None:
    if not message.document or not message.document.mime_type or not message.document.mime_type.startswith("image/"):
        await message.answer("Пришли изображение (photo или image-файл).")
        return
    await _process_image(message, state, bot, settings, user_sheets, sheets, attendance_llm)


@router.callback_query(ConfirmCb.filter(F.action == "cancel"))
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer("Ок, отменил. /start чтобы начать заново.")
    await callback.answer()


@router.callback_query(ConfirmCb.filter(F.action == "apply"))
async def cb_apply(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Flow.waiting_column)
    if callback.message:
        await callback.message.answer("Введи колонку (например S или AA):", reply_markup=back_keyboard())
    await callback.answer()


@router.callback_query(ConfirmCb.filter(F.action == "back"))
async def cb_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Flow.waiting_confirm)
    if callback.message:
        await callback.message.answer("Ок. Нажми «Применить» или «Отмена».")
    await callback.answer()


@router.message(Flow.waiting_column, F.text)
async def apply_column(
    message: Message,
    state: FSMContext,
    settings: Settings,
    user_sheets: SQLiteUserSheetRepository,
    sheets: GoogleSheetsService,
) -> None:
    assert message.from_user is not None
    user_id = message.from_user.id

    col = normalize_column(message.text or "")
    if not is_valid_column(col):
        await message.answer("Не похоже на колонку. Пример: S или AA")
        return

    data = await state.get_data()
    roster_entries: list[dict[str, Any]] = data.get("roster_entries") or []
    simple: dict[str, int] = data.get("simple") or {}

    if not roster_entries or not simple:
        await message.answer("Нет сохранённого результата. /start чтобы начать заново.")
        await state.clear()
        return

    rows = [int(x["row"]) for x in roster_entries]
    start_row, end_row = min(rows), max(rows)

    sheet_id = await _effective_sheet_id(user_id, settings, user_sheets)
    if not sheet_id:
        await message.answer("Не задана таблица. /sheet <code>ID</code>")
        await state.clear()
        return

    try:
        current_vals = await sheets.get_column_values(
            sheet_id,
            settings.worksheet_name,
            col,
            start_row,
            end_row,
        )
    except Exception as e:
        logger.exception("Failed to read column values")
        await message.answer(f"Не смог прочитать колонку {col}: {html.escape(str(e))}")
        return

    updated = list(current_vals)
    changed = 0

    for entry in roster_entries:
        row = int(entry["row"])
        name = str(entry["name"]).strip()

        if int(simple.get(name, 0)) != 1:
            continue

        idx = row - start_row
        cur = updated[idx]

        try:
            cur_num = float(str(cur).replace(",", "."))
        except Exception:
            cur_num = 0.0

        if cur_num >= 2:
            continue

        if str(cur).strip() != "1":
            updated[idx] = 1
            changed += 1

    try:
        await sheets.set_column_values(
            sheet_id,
            settings.worksheet_name,
            col,
            start_row,
            end_row,
            updated,
        )
    except Exception as e:
        logger.exception("Failed to write column values")
        await message.answer(f"Не смог записать в таблицу: {html.escape(str(e))}")
        return

    await message.answer(f"✅ Готово. Вписал 1 в колонку {col} для {changed} студентов.")
    await state.clear()
