"""
State machine for order flow - complete version with all states.
"""
from enum import Enum
from typing import Dict, Any, Optional


class OrderState(Enum):
    """Order flow states - complete flow"""
    START = "start"
    ASK_ORDER_TYPE = "ask_order_type"
    SHOW_CATALOG = "show_catalog"
    ASK_WEIGHT = "ask_weight"
    ASK_QUANTITY = "ask_quantity"
    ASK_DECOR_TYPE = "ask_decor_type"
    ASK_INSCRIPTION = "ask_inscription"
    ASK_ADDONS = "ask_addons"
    ASK_PICKUP_LOCATION = "ask_pickup_location"
    ASK_ISSUE_TIME = "ask_issue_time"
    ASK_PHONE = "ask_phone"
    CHECK_CONSENT = "check_consent"
    SHOW_PRIVACY_POLICY = "show_privacy_policy"
    CONFIRM_ORDER = "confirm_order"
    COMPLETED = "completed"


class OrderFlowStateMachine:
    """State machine for order flow (minimal implementation for compatibility)"""
    def __init__(self):
        pass
