from aiogram.fsm.state import State, StatesGroup


class Flow(StatesGroup):
    waiting_sheet_id = State()
    waiting_image = State()
    waiting_confirm = State()
    waiting_column = State()
