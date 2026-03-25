"""FSM states for manual gift purchase and sale capture."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class TradeCaptureStates(StatesGroup):
    """Conversation states for explicit purchase and sale flows."""

    waiting_for_purchase_input = State()
    waiting_for_purchase_marketplace = State()
    waiting_for_purchase_price = State()
    waiting_for_purchase_rate_choice = State()
    waiting_for_purchase_rate_date = State()
    waiting_for_sale_input = State()
    waiting_for_sale_marketplace = State()
    waiting_for_sale_price = State()
    waiting_for_sale_rate_choice = State()
    waiting_for_sale_rate_date = State()
    waiting_for_sale_fee = State()
