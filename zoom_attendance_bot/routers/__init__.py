from __future__ import annotations

from aiogram import Router

from ..filters.admin_only import AdminOnly
from .attendance import router as attendance_router
from .common import router as common_router
from .sheet import router as sheet_router


def build_router() -> Router:
    root = Router(name="root")

    root.message.filter(AdminOnly())
    root.callback_query.filter(AdminOnly())

    root.include_router(common_router)
    root.include_router(sheet_router)
    root.include_router(attendance_router)

    return root
