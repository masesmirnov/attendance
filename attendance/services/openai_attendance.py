from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field


ATTENDANCE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["participants_extracted", "marks"],
    "properties": {
        "participants_extracted": {"type": "array", "items": {"type": "string"}},
        "marks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["roster_name", "mark", "confidence", "matched_participant"],
                "properties": {
                    "roster_name": {"type": "string"},
                    "mark": {"type": "integer", "enum": [0, 1]},
                    "matched_participant": {"type": ["string", "null"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        },
    },
}

INSTRUCTIONS = (
    "У тебя есть скриншот, на котором видно присутствующих (участники созвона, чат, список — откуда угодно), "
    "и roster (реестр студентов).\n"
    "1) извлеки все имена со скриншота -> participants_extracted\n"
    "2) сопоставь участников с roster (кириллица/латиница, транслит, опечатки, инициалы, порядок имя/фамилия)\n"
    "3) верни marks: РОВНО один объект на КАЖДОЕ имя из roster:\n"
    "   - roster_name: строго строка из roster\n"
    "   - mark: 1 если присутствует на скрине, иначе 0\n"
    "   - matched_participant: как на скрине или null\n"
    "   - confidence: 0..1\n"
    "Ничего кроме JSON не выводи."
)


class AttendanceMark(BaseModel):
    roster_name: str
    mark: int = Field(ge=0, le=1)
    matched_participant: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class AttendanceOutput(BaseModel):
    participants_extracted: list[str]
    marks: list[AttendanceMark]


def _to_data_url(image_bytes: bytes, mime_type: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


@dataclass(slots=True, frozen=True)
class AttendanceLLM:
    client: AsyncOpenAI
    model: str
    store: bool = False

    async def analyze(self, roster: list[str], image_bytes: bytes, mime_type: str) -> AttendanceOutput:
        user_text = "ROSTER:\n" + json.dumps(roster, ensure_ascii=False)

        resp = await self.client.responses.create(
            model=self.model,
            instructions=INSTRUCTIONS,
            store=self.store,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": user_text},
                        {"type": "input_image", "image_url": _to_data_url(image_bytes, mime_type)},
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "attendance",
                    "description": "Attendance extraction and roster matching result",
                    "strict": True,
                    "schema": ATTENDANCE_JSON_SCHEMA,
                }
            },
        )

        data = json.loads(resp.output_text)
        return AttendanceOutput.model_validate(data)

    @staticmethod
    def marks_to_map(attendance: AttendanceOutput, roster: list[str]) -> dict[str, int]:
        got = {m.roster_name: int(m.mark) for m in attendance.marks}
        return {name: int(got.get(name, 0)) for name in roster}
