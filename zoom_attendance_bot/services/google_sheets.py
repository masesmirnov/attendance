from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


@dataclass(slots=True, frozen=True)
class RosterEntry:
    row: int
    name: str


class GoogleSheetsClient:
    def __init__(self, service_account_info: Mapping[str, Any]):
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(dict(service_account_info), scopes=scopes)
        self._svc = build("sheets", "v4", credentials=creds, cache_discovery=False)

    def get_roster(self, sheet_id: str, worksheet: str, name_col: str, start_row: int) -> list[RosterEntry]:
        rng = f"{worksheet}!{name_col}{start_row}:{name_col}"
        resp = self._svc.spreadsheets().values().get(spreadsheetId=sheet_id, range=rng).execute()
        values = resp.get("values", [])

        out: list[RosterEntry] = []
        for i, row in enumerate(values):
            name = (row[0] if row else "")
            name = str(name).strip()
            if name:
                out.append(RosterEntry(row=start_row + i, name=name))
        return out

    def get_column_values(
        self, sheet_id: str, worksheet: str, col: str, start_row: int, end_row: int
    ) -> list[Any]:
        rng = f"{worksheet}!{col}{start_row}:{col}{end_row}"
        resp = self._svc.spreadsheets().values().get(spreadsheetId=sheet_id, range=rng).execute()
        values = resp.get("values", [])

        out: list[Any] = []
        for r in range(start_row, end_row + 1):
            idx = r - start_row
            if idx < len(values) and values[idx]:
                out.append(values[idx][0])
            else:
                out.append("")
        return out

    def set_column_values(
        self,
        sheet_id: str,
        worksheet: str,
        col: str,
        start_row: int,
        end_row: int,
        values: list[Any],
    ) -> None:
        expected = end_row - start_row + 1
        if len(values) != expected:
            raise ValueError(f"values length mismatch: expected {expected}, got {len(values)}")

        rng = f"{worksheet}!{col}{start_row}:{col}{end_row}"
        body = {"values": [[v] for v in values]}
        self._svc.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=rng,
            valueInputOption="RAW",
            body=body,
        ).execute()


class GoogleSheetsService:
    def __init__(self, client: GoogleSheetsClient):
        self._client = client

    async def get_roster(self, sheet_id: str, worksheet: str, name_col: str, start_row: int) -> list[RosterEntry]:
        return await asyncio.to_thread(self._client.get_roster, sheet_id, worksheet, name_col, start_row)

    async def get_column_values(
        self, sheet_id: str, worksheet: str, col: str, start_row: int, end_row: int
    ) -> list[Any]:
        return await asyncio.to_thread(
            self._client.get_column_values, sheet_id, worksheet, col, start_row, end_row
        )

    async def set_column_values(
        self,
        sheet_id: str,
        worksheet: str,
        col: str,
        start_row: int,
        end_row: int,
        values: list[Any],
    ) -> None:
        await asyncio.to_thread(
            self._client.set_column_values, sheet_id, worksheet, col, start_row, end_row, values
        )
