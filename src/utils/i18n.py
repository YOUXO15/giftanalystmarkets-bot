"""Lightweight runtime localization helpers."""

from __future__ import annotations

from src.utils.enums import Language


_TEXTS: dict[str, dict[Language, str]] = {
    "registration_required": {
        Language.RU: "\u041f\u043e\u0445\u043e\u0436\u0435, \u0442\u044b \u0435\u0449\u0435 \u043d\u0435 \u0437\u0430\u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0438\u0440\u043e\u0432\u0430\u043d. \u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0437\u0430\u043f\u0443\u0441\u0442\u0438 /start.",
        Language.EN: "Looks like you are not registered yet. Run /start first.",
        Language.ZH: "\u4f60\u8fd8\u6ca1\u6709\u6ce8\u518c\u3002\u8bf7\u5148\u8f93\u5165 /start\u3002",
    },
    "settings_not_found": {
        Language.RU: "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b. \u0412\u044b\u043f\u043e\u043b\u043d\u0438 /start, \u0447\u0442\u043e\u0431\u044b \u0438\u043d\u0438\u0446\u0438\u0430\u043b\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043f\u0440\u043e\u0444\u0438\u043b\u044c.",
        Language.EN: "Settings were not found. Run /start to initialize your profile.",
        Language.ZH: "\u672a\u627e\u5230\u8bbe\u7f6e\u3002\u8bf7\u5148\u8f93\u5165 /start \u521d\u59cb\u5316\u4f60\u7684\u8d44\u6599\u3002",
    },
    "settings_title": {
        Language.RU: "<b>\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f</b>",
        Language.EN: "<b>User Settings</b>",
        Language.ZH: "<b>\u7528\u6237\u8bbe\u7f6e</b>",
    },
    "settings_label_notifications": {
        Language.RU: "\u0423\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u044f",
        Language.EN: "Notifications",
        Language.ZH: "\u901a\u77e5",
    },
    "settings_label_autosync": {
        Language.RU: "\u0410\u0432\u0442\u043e\u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f",
        Language.EN: "Auto sync",
        Language.ZH: "\u81ea\u52a8\u540c\u6b65",
    },
    "settings_label_currency": {
        Language.RU: "\u0412\u0430\u043b\u044e\u0442\u0430 \u043e\u0442\u0447\u0451\u0442\u043e\u0432",
        Language.EN: "Report currency",
        Language.ZH: "\u62a5\u8868\u8d27\u5e01",
    },
    "settings_label_subscription": {
        Language.RU: "\u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430",
        Language.EN: "Subscription",
        Language.ZH: "\u8ba2\u9605",
    },
    "settings_label_language": {
        Language.RU: "\u042f\u0437\u044b\u043a",
        Language.EN: "Language",
        Language.ZH: "\u8bed\u8a00",
    },
    "settings_subscription_inactive": {
        Language.RU: "\u043d\u0435 \u0430\u043a\u0442\u0438\u0432\u0438\u0440\u043e\u0432\u0430\u043d\u0430",
        Language.EN: "inactive",
        Language.ZH: "\u672a\u6fc0\u6d3b",
    },
    "settings_subscription_active": {
        Language.RU: "\u0430\u043a\u0442\u0438\u0432\u043d\u0430",
        Language.EN: "active",
        Language.ZH: "\u5df2\u6fc0\u6d3b",
    },
    "settings_subscription_expired": {
        Language.RU: "\u0438\u0441\u0442\u0435\u043a\u043b\u0430",
        Language.EN: "expired",
        Language.ZH: "\u5df2\u8fc7\u671f",
    },
    "settings_subscription_until": {
        Language.RU: "{status} \u0434\u043e {date}",
        Language.EN: "{status} until {date}",
        Language.ZH: "{status}\uff0c\u76f4\u5230 {date}",
    },
    "feature_notifications_title": {
        Language.RU: "\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u044f\u043c\u0438",
        Language.EN: "Notifications Management",
        Language.ZH: "\u901a\u77e5\u7ba1\u7406",
    },
    "autosync_info": {
        Language.RU: (
            "<b>\u0410\u0432\u0442\u043e\u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f</b>\n\n"
            "\u0421\u0435\u0439\u0447\u0430\u0441 \u0431\u043e\u0442 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0432 \u0440\u0443\u0447\u043d\u043e\u043c \u0440\u0435\u0436\u0438\u043c\u0435: "
            "\u043f\u043e\u043a\u0443\u043f\u043a\u0438 \u0434\u043e\u0431\u0430\u0432\u043b\u044f\u044e\u0442\u0441\u044f \u043f\u043e \u0441\u0441\u044b\u043b\u043a\u0435 \u0438\u043b\u0438 \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u044e, "
            "\u0430 \u043f\u0440\u043e\u0434\u0430\u0436\u0438 \u0437\u0430\u043a\u0440\u044b\u0432\u0430\u044e\u0442\u0441\u044f \u043f\u043e \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u044f\u043c \u043c\u0430\u0440\u043a\u0435\u0442\u043f\u043b\u0435\u0439\u0441\u043e\u0432. "
            "\u0412\u043d\u0435\u0448\u043d\u0438\u0439 API-\u0441\u0438\u043d\u043a \u0432 MVP \u043e\u0442\u043a\u043b\u044e\u0447\u0435\u043d."
        ),
        Language.EN: (
            "<b>Auto Sync</b>\n\n"
            "The bot now works in manual mode: purchases are added from gift links or marketplace notifications, "
            "and sales are matched by sale notifications. External API auto-sync is disabled in MVP."
        ),
        Language.ZH: (
            "<b>\u81ea\u52a8\u540c\u6b65</b>\n\n"
            "\u5f53\u524d\u673a\u5668\u4eba\u4ee5\u624b\u52a8\u6a21\u5f0f\u8fd0\u884c\uff1a\u8d2d\u4e70\u901a\u8fc7\u793c\u7269\u94fe\u63a5\u6216\u5e02\u573a\u901a\u77e5\u6dfb\u52a0\uff0c"
            "\u9500\u552e\u901a\u8fc7\u9500\u552e\u901a\u77e5\u8fdb\u884c\u5339\u914d\u3002MVP \u9636\u6bb5\u5df2\u5173\u95ed\u5916\u90e8 API \u81ea\u52a8\u540c\u6b65\u3002"
        ),
    },
    "language_menu_title": {
        Language.RU: "<b>\u0412\u044b\u0431\u043e\u0440 \u044f\u0437\u044b\u043a\u0430</b>\n\n\u0412\u044b\u0431\u0435\u0440\u0438 \u044f\u0437\u044b\u043a \u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441\u0430:",
        Language.EN: "<b>Language Selection</b>\n\nChoose your interface language:",
        Language.ZH: "<b>\u8bed\u8a00\u9009\u62e9</b>\n\n\u8bf7\u9009\u62e9\u754c\u9762\u8bed\u8a00\uff1a",
    },
    "language_changed": {
        Language.RU: "\u042f\u0437\u044b\u043a \u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441\u0430 \u043e\u0431\u043d\u043e\u0432\u043b\u0451\u043d.",
        Language.EN: "Interface language has been updated.",
        Language.ZH: "\u754c\u9762\u8bed\u8a00\u5df2\u66f4\u65b0\u3002",
    },
    "back_to_main_menu": {
        Language.RU: "\u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e \u0441\u043d\u043e\u0432\u0430 \u043f\u0435\u0440\u0435\u0434 \u0442\u043e\u0431\u043e\u0439.",
        Language.EN: "Main menu is open again.",
        Language.ZH: "\u4e3b\u83dc\u5355\u5df2\u91cd\u65b0\u6253\u5f00\u3002",
    },
    "welcome_new": {
        Language.RU: (
            "<b>\u0420\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044f \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430, {first_name}!</b>\n\n"
            "\u042f \u043f\u043e\u043c\u043e\u0433\u0430\u044e \u0432\u0435\u0441\u0442\u0438 \u0443\u0447\u0451\u0442 Telegram-\u043f\u043e\u0434\u0430\u0440\u043a\u043e\u0432: "
            "\u0441\u043e\u0445\u0440\u0430\u043d\u044f\u044e \u043f\u043e\u043a\u0443\u043f\u043a\u0438/\u043f\u0440\u043e\u0434\u0430\u0436\u0438, \u0441\u0447\u0438\u0442\u0430\u044e \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0443 \u0438 \u0433\u043e\u0442\u043e\u0432\u043b\u044e CSV/XLSX-\u044d\u043a\u0441\u043f\u043e\u0440\u0442.\n\n"
            "\u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430: <b>{price_ton} TON</b> \u0437\u0430 30 \u0434\u043d\u0435\u0439."
        ),
        Language.EN: (
            "<b>Registration completed, {first_name}!</b>\n\n"
            "I help you track Telegram gifts: store purchases/sales, build stats, and export CSV/XLSX reports.\n\n"
            "Subscription: <b>{price_ton} TON</b> for 30 days."
        ),
        Language.ZH: (
            "<b>\u6ce8\u518c\u5b8c\u6210\uff0c{first_name}\uff01</b>\n\n"
            "\u6211\u53ef\u4ee5\u5e2e\u4f60\u8bb0\u5f55 Telegram \u793c\u7269\u4ea4\u6613\uff1a\u4fdd\u5b58\u4e70\u5165/\u5356\u51fa\uff0c\u751f\u6210\u7edf\u8ba1\uff0c\u5e76\u5bfc\u51fa CSV/XLSX \u62a5\u8868\u3002\n\n"
            "\u8ba2\u9605\u4ef7\u683c\uff1a\u6bcf 30 \u5929 <b>{price_ton} TON</b>\u3002"
        ),
    },
    "welcome_returning": {
        Language.RU: (
            "<b>\u0421 \u0432\u043e\u0437\u0432\u0440\u0430\u0449\u0435\u043d\u0438\u0435\u043c, {first_name}!</b>\n\n"
            "\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0430\u0435\u043c \u0443\u0447\u0435\u0442 \u043f\u043e \u0442\u0432\u043e\u0438\u043c \u0441\u0434\u0435\u043b\u043a\u0430\u043c. \u0412\u0441\u0435 \u043e\u0441\u043d\u043e\u0432\u043d\u044b\u0435 \u0440\u0430\u0437\u0434\u0435\u043b\u044b \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b \u0432 \u043c\u0435\u043d\u044e \u043d\u0438\u0436\u0435."
        ),
        Language.EN: (
            "<b>Welcome back, {first_name}!</b>\n\n"
            "Let\u2019s continue tracking your deals. All core sections are available in the menu below."
        ),
        Language.ZH: (
            "<b>\u6b22\u8fce\u56de\u6765\uff0c{first_name}\uff01</b>\n\n"
            "\u6211\u4eec\u7ee7\u7eed\u8ddf\u8e2a\u4f60\u7684\u4ea4\u6613\u3002\u6240\u6709\u529f\u80fd\u90fd\u5728\u4e0b\u65b9\u83dc\u5355\u4e2d\u3002"
        ),
    },
    "help_text": {
        Language.RU: (
            "<b>\u0427\u0442\u043e \u0443\u043c\u0435\u0435\u0442 \u0431\u043e\u0442</b>\n"
            "/start - \u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044f \u0438 \u0433\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e\n"
            "/help - \u0441\u043f\u0440\u0430\u0432\u043a\u0430\n"
            "/sync - \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043a\u0443\u043f\u043b\u0435\u043d\u043d\u044b\u0439 \u043f\u043e\u0434\u0430\u0440\u043e\u043a\n"
            "/sale - \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u0440\u043e\u0434\u0430\u043d\u043d\u044b\u0439 \u043f\u043e\u0434\u0430\u0440\u043e\u043a\n"
            "/deals - \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0435 \u0441\u0434\u0435\u043b\u043a\u0438\n"
            "/stats - \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430\n"
            "/ton - \u043a\u0443\u0440\u0441 TON\n"
            "/export - \u044d\u043a\u0441\u043f\u043e\u0440\u0442 CSV/XLSX\n"
            "/pay - \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0430 \u0438 \u043e\u043f\u043b\u0430\u0442\u0430\n"
            "/balance - \u0432\u043d\u0443\u0442\u0440\u0435\u043d\u043d\u0438\u0439 \u0431\u0430\u043b\u0430\u043d\u0441\n"
            "/referrals - \u0440\u0435\u0444\u0435\u0440\u0430\u043b\u044c\u043d\u0430\u044f \u0441\u0441\u044b\u043b\u043a\u0430\n"
            "/gift - \u043f\u043e\u0434\u0430\u0440\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443\n"
            "/withdraw - \u0437\u0430\u043f\u0440\u043e\u0441 \u043d\u0430 \u0432\u044b\u0432\u043e\u0434\n"
            "/settings - \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438"
        ),
        Language.EN: (
            "<b>Bot commands</b>\n"
            "/start - register and open main menu\n"
            "/help - show help\n"
            "/sync - add purchased gift\n"
            "/sale - add sold gift\n"
            "/deals - recent deals\n"
            "/stats - statistics\n"
            "/ton - TON rate\n"
            "/export - CSV/XLSX export\n"
            "/pay - subscription and payment\n"
            "/balance - internal balance\n"
            "/referrals - referral link\n"
            "/gift - gift subscription\n"
            "/withdraw - withdrawal request\n"
            "/settings - user settings"
        ),
        Language.ZH: (
            "<b>\u673a\u5668\u4eba\u529f\u80fd</b>\n"
            "/start - \u6ce8\u518c\u5e76\u6253\u5f00\u4e3b\u83dc\u5355\n"
            "/help - \u5e2e\u52a9\n"
            "/sync - \u6dfb\u52a0\u5df2\u8d2d\u4e70\u793c\u7269\n"
            "/sale - \u6dfb\u52a0\u5df2\u552e\u51fa\u793c\u7269\n"
            "/deals - \u6700\u8fd1\u4ea4\u6613\n"
            "/stats - \u7edf\u8ba1\n"
            "/ton - TON \u6c47\u7387\n"
            "/export - CSV/XLSX \u5bfc\u51fa\n"
            "/pay - \u8ba2\u9605\u4e0e\u652f\u4ed8\n"
            "/balance - \u5185\u90e8\u4f59\u989d\n"
            "/referrals - \u63a8\u8350\u94fe\u63a5\n"
            "/gift - \u8d60\u9001\u8ba2\u9605\n"
            "/withdraw - \u63d0\u73b0\u7533\u8bf7\n"
            "/settings - \u7528\u6237\u8bbe\u7f6e"
        ),
    },
}


_BUTTONS: dict[str, dict[Language, str]] = {
    "add_purchase": {
        Language.RU: "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043a\u0443\u043f\u043b\u0435\u043d\u043d\u044b\u0439 \u043f\u043e\u0434\u0430\u0440\u043e\u043a",
        Language.EN: "Add Purchased Gift",
        Language.ZH: "\u6dfb\u52a0\u5df2\u8d2d\u4e70\u793c\u7269",
    },
    "add_sale": {
        Language.RU: "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u0440\u043e\u0434\u0430\u043d\u043d\u044b\u0439 \u043f\u043e\u0434\u0430\u0440\u043e\u043a",
        Language.EN: "Add Sold Gift",
        Language.ZH: "\u6dfb\u52a0\u5df2\u552e\u51fa\u793c\u7269",
    },
    "deals": {
        Language.RU: "\u0421\u0434\u0435\u043b\u043a\u0438",
        Language.EN: "Deals",
        Language.ZH: "\u4ea4\u6613",
    },
    "stats": {
        Language.RU: "\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430",
        Language.EN: "Stats",
        Language.ZH: "\u7edf\u8ba1",
    },
    "ton": {
        Language.RU: "\u041a\u0443\u0440\u0441 TON",
        Language.EN: "TON Rate",
        Language.ZH: "TON \u6c47\u7387",
    },
    "export": {
        Language.RU: "\u042d\u043a\u0441\u043f\u043e\u0440\u0442",
        Language.EN: "Export",
        Language.ZH: "\u5bfc\u51fa",
    },
    "subscription": {
        Language.RU: "\u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430",
        Language.EN: "Subscription",
        Language.ZH: "\u8ba2\u9605",
    },
    "balance": {
        Language.RU: "\u0411\u0430\u043b\u0430\u043d\u0441",
        Language.EN: "Balance",
        Language.ZH: "\u4f59\u989d",
    },
    "referrals": {
        Language.RU: "\u0420\u0435\u0444\u0435\u0440\u0430\u043b\u044b",
        Language.EN: "Referrals",
        Language.ZH: "\u63a8\u8350",
    },
    "gift_subscription": {
        Language.RU: "\u041f\u043e\u0434\u0430\u0440\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443",
        Language.EN: "Gift Subscription",
        Language.ZH: "\u8d60\u9001\u8ba2\u9605",
    },
    "withdraw": {
        Language.RU: "\u0412\u044b\u0432\u043e\u0434",
        Language.EN: "Withdraw",
        Language.ZH: "\u63d0\u73b0",
    },
    "settings": {
        Language.RU: "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438",
        Language.EN: "Settings",
        Language.ZH: "\u8bbe\u7f6e",
    },
    "notifications": {
        Language.RU: "\u0423\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u044f",
        Language.EN: "Notifications",
        Language.ZH: "\u901a\u77e5",
    },
    "autosync": {
        Language.RU: "\u0410\u0432\u0442\u043e\u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f",
        Language.EN: "Auto Sync",
        Language.ZH: "\u81ea\u52a8\u540c\u6b65",
    },
    "language": {
        Language.RU: "\u042f\u0437\u044b\u043a",
        Language.EN: "Language",
        Language.ZH: "\u8bed\u8a00",
    },
    "back": {
        Language.RU: "\u041d\u0430\u0437\u0430\u0434",
        Language.EN: "Back",
        Language.ZH: "\u8fd4\u56de",
    },
    "subscription_create": {
        Language.RU: "\u041e\u043f\u043b\u0430\u0442\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443",
        Language.EN: "Pay Subscription",
        Language.ZH: "\u652f\u4ed8\u8ba2\u9605",
    },
    "subscription_check": {
        Language.RU: "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u043e\u043f\u043b\u0430\u0442\u0443",
        Language.EN: "Check Payment",
        Language.ZH: "\u68c0\u67e5\u652f\u4ed8",
    },
    "subscription_balance_pay": {
        Language.RU: "\u041e\u043f\u043b\u0430\u0442\u0438\u0442\u044c \u0441 \u0431\u0430\u043b\u0430\u043d\u0441\u0430",
        Language.EN: "Pay from Balance",
        Language.ZH: "\u4f59\u989d\u652f\u4ed8",
    },
    "back_to_menu": {
        Language.RU: "\u0412 \u043c\u0435\u043d\u044e",
        Language.EN: "Menu",
        Language.ZH: "\u83dc\u5355",
    },
    "cancel": {
        Language.RU: "\u041e\u0442\u043c\u0435\u043d\u0430",
        Language.EN: "Cancel",
        Language.ZH: "\u53d6\u6d88",
    },
    "language_ru": {
        Language.RU: "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
        Language.EN: "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
        Language.ZH: "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
    },
    "language_en": {
        Language.RU: "English",
        Language.EN: "English",
        Language.ZH: "English",
    },
    "language_zh": {
        Language.RU: "\u4e2d\u6587",
        Language.EN: "\u4e2d\u6587",
        Language.ZH: "\u4e2d\u6587",
    },
}


def normalize_language(value: Language | str | None) -> Language:
    """Normalize any language-like value to a supported language enum."""

    if isinstance(value, Language):
        return value
    if value is None:
        return Language.RU
    raw = str(value).strip().lower()
    if raw.startswith("zh"):
        return Language.ZH
    if raw.startswith("en"):
        return Language.EN
    if raw.startswith("ru"):
        return Language.RU
    return Language.RU


def language_from_telegram_code(language_code: str | None) -> Language:
    """Resolve user language from Telegram `language_code`."""

    return normalize_language(language_code)


def t(key: str, language: Language | str | None, **kwargs: object) -> str:
    """Translate a text key with optional format placeholders."""

    lang = normalize_language(language)
    catalog = _TEXTS.get(key)
    if catalog is None:
        return key
    template = catalog.get(lang) or catalog[Language.RU]
    return template.format(**kwargs)


def button_text(key: str, language: Language | str | None) -> str:
    """Return translated text for a semantic button key."""

    lang = normalize_language(language)
    catalog = _BUTTONS.get(key)
    if catalog is None:
        return key
    return catalog.get(lang) or catalog[Language.RU]


def button_variants(key: str) -> set[str]:
    """Return all language variants for a semantic button key."""

    catalog = _BUTTONS.get(key)
    if catalog is None:
        return {key}
    return {value for value in catalog.values()}
