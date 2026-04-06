"""FSM states for referral balance actions."""

from aiogram.fsm.state import State, StatesGroup


class ReferralStates(StatesGroup):
    """User interaction states for gifting and withdrawals."""

    waiting_for_gift_target = State()
    waiting_for_withdraw_details = State()
