from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from openai import AsyncOpenAI

from .config import Settings
from .logging_setup import setup_logging
from .repositories.user_sheets import SQLiteUserSheetRepository
from .routers import build_router
from .services.google_sheets import GoogleSheetsClient, GoogleSheetsService
from .services.openai_attendance import AttendanceLLM


async def main() -> None:
    settings = Settings()

    setup_logging(settings.log_level)
    log = logging.getLogger(__name__)

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(build_router())

    user_sheets = await SQLiteUserSheetRepository.create(settings.user_sheet_db_path)

    async with Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    ) as bot:
        async with AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value()) as openai_client:
            sheets_client = GoogleSheetsClient(settings.google_service_account_info)
            sheets = GoogleSheetsService(sheets_client)
            attendance_llm = AttendanceLLM(
                client=openai_client,
                model=settings.openai_model,
                store=settings.openai_store,
            )

            log.info("Bot started")

            try:
                await dp.start_polling(
                    bot,
                    tasks_concurrency_limit=settings.polling_concurrency_limit,
                    settings=settings,
                    user_sheets=user_sheets,
                    sheets=sheets,
                    attendance_llm=attendance_llm,
                )
            finally:
                await user_sheets.close()
                log.info("Bot stopped")


def run() -> None:
    asyncio.run(main())
