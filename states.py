from aiogram.fsm.state import StatesGroup, State

class OrderStates(StatesGroup):
    waiting_for_scan = State()