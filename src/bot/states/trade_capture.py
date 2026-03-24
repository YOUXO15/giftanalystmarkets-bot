"""FSM states for manual deal intake flow."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class TradeCaptureStates(StatesGroup):
    """Conversation states for manual purchase intake."""

    waiting_for_gift_link = State()
    waiting_for_buy_price = State()
    waiting_for_rate_choice = State()
    waiting_for_rate_date = State()
    waiting_for_sale_fee = State()
