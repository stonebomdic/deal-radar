from __future__ import annotations

from typing import Any, Dict, List

from src.models import CreditCard, Promotion
from src.notifications.telegram import escape_markdown_v2

# Discord embed colors by notification type
COLOR_NEW_PROMOTION = 0x00CC66  # green
COLOR_EXPIRING_PROMOTION = 0xFF9900  # orange
COLOR_NEW_CARD = 0x3399FF  # blue


def format_new_promotions(promotions: List[Promotion]) -> Dict[str, Any]:
    """Format new promotions for all channels.

    Returns:
        dict with keys "telegram" (str) and "discord_embeds" (list).
    """
    if not promotions:
        return {"telegram": "", "discord_embeds": []}

    # Telegram MarkdownV2
    lines = [escape_markdown_v2("--- 新優惠通知 ---"), ""]
    for promo in promotions:
        card_name = promo.card.name if promo.card else "Unknown"
        bank_name = promo.card.bank.name if promo.card and promo.card.bank else "Unknown"
        lines.append(f"*{escape_markdown_v2(promo.title)}*")
        lines.append(
            f"{escape_markdown_v2(bank_name)} / {escape_markdown_v2(card_name)}"
        )
        if promo.reward_rate is not None:
            lines.append(
                f"{escape_markdown_v2('回饋率:')} {escape_markdown_v2(f'{promo.reward_rate}%')}"
            )
        if promo.end_date:
            lines.append(
                f"{escape_markdown_v2('截止日:')} {escape_markdown_v2(str(promo.end_date))}"
            )
        lines.append("")
    telegram_text = "\n".join(lines).strip()

    # Discord embeds
    discord_embeds = []
    for promo in promotions:
        card_name = promo.card.name if promo.card else "Unknown"
        bank_name = promo.card.bank.name if promo.card and promo.card.bank else "Unknown"
        fields = [
            {"name": "Bank", "value": bank_name, "inline": True},
            {"name": "Card", "value": card_name, "inline": True},
        ]
        if promo.reward_rate is not None:
            fields.append(
                {"name": "Reward Rate", "value": f"{promo.reward_rate}%", "inline": True}
            )
        if promo.end_date:
            fields.append(
                {"name": "Expires", "value": str(promo.end_date), "inline": True}
            )
        if promo.description:
            fields.append(
                {"name": "Details", "value": promo.description[:200], "inline": False}
            )
        embed = {
            "title": promo.title,
            "color": COLOR_NEW_PROMOTION,
            "fields": fields,
            "footer": {"text": f"{bank_name} - {card_name}"},
        }
        discord_embeds.append(embed)

    return {"telegram": telegram_text, "discord_embeds": discord_embeds}


def format_expiring_promotions(promotions: List[Promotion]) -> Dict[str, Any]:
    """Format expiring promotions for all channels.

    Returns:
        dict with keys "telegram" (str) and "discord_embeds" (list).
    """
    if not promotions:
        return {"telegram": "", "discord_embeds": []}

    # Telegram MarkdownV2
    lines = [escape_markdown_v2("--- 即將到期優惠提醒 ---"), ""]
    for promo in promotions:
        card_name = promo.card.name if promo.card else "Unknown"
        bank_name = promo.card.bank.name if promo.card and promo.card.bank else "Unknown"
        lines.append(f"*{escape_markdown_v2(promo.title)}*")
        lines.append(
            f"{escape_markdown_v2(bank_name)} / {escape_markdown_v2(card_name)}"
        )
        if promo.end_date:
            lines.append(
                f"{escape_markdown_v2('到期日:')} {escape_markdown_v2(str(promo.end_date))}"
            )
        lines.append("")
    telegram_text = "\n".join(lines).strip()

    # Discord embeds
    discord_embeds = []
    for promo in promotions:
        card_name = promo.card.name if promo.card else "Unknown"
        bank_name = promo.card.bank.name if promo.card and promo.card.bank else "Unknown"
        fields = [
            {"name": "Bank", "value": bank_name, "inline": True},
            {"name": "Card", "value": card_name, "inline": True},
        ]
        if promo.end_date:
            fields.append(
                {"name": "Expires", "value": str(promo.end_date), "inline": True}
            )
        embed = {
            "title": f"[Expiring] {promo.title}",
            "color": COLOR_EXPIRING_PROMOTION,
            "fields": fields,
            "footer": {"text": f"{bank_name} - {card_name}"},
        }
        discord_embeds.append(embed)

    return {"telegram": telegram_text, "discord_embeds": discord_embeds}


def format_new_cards(cards: List[CreditCard]) -> Dict[str, Any]:
    """Format new credit cards for all channels.

    Returns:
        dict with keys "telegram" (str) and "discord_embeds" (list).
    """
    if not cards:
        return {"telegram": "", "discord_embeds": []}

    # Telegram MarkdownV2
    lines = [escape_markdown_v2("--- 新信用卡通知 ---"), ""]
    for card in cards:
        bank_name = card.bank.name if card.bank else "Unknown"
        lines.append(f"*{escape_markdown_v2(card.name)}*")
        lines.append(f"{escape_markdown_v2(bank_name)}")
        if card.card_type:
            lines.append(
                f"{escape_markdown_v2('卡別:')} {escape_markdown_v2(card.card_type)}"
            )
        if card.annual_fee is not None:
            fee_str = "免年費" if card.annual_fee == 0 else f"${card.annual_fee}"
            lines.append(
                f"{escape_markdown_v2('年費:')} {escape_markdown_v2(fee_str)}"
            )
        if card.base_reward_rate is not None:
            lines.append(
                f"{escape_markdown_v2('基本回饋:')} "
                f"{escape_markdown_v2(f'{card.base_reward_rate}%')}"
            )
        lines.append("")
    telegram_text = "\n".join(lines).strip()

    # Discord embeds
    discord_embeds = []
    for card in cards:
        bank_name = card.bank.name if card.bank else "Unknown"
        fields = [
            {"name": "Bank", "value": bank_name, "inline": True},
        ]
        if card.card_type:
            fields.append(
                {"name": "Card Type", "value": card.card_type, "inline": True}
            )
        if card.annual_fee is not None:
            fee_str = "Free" if card.annual_fee == 0 else f"${card.annual_fee}"
            fields.append(
                {"name": "Annual Fee", "value": fee_str, "inline": True}
            )
        if card.base_reward_rate is not None:
            fields.append(
                {"name": "Base Reward", "value": f"{card.base_reward_rate}%", "inline": True}
            )
        if card.annual_fee_waiver:
            fields.append(
                {"name": "Fee Waiver", "value": card.annual_fee_waiver, "inline": False}
            )
        embed = {
            "title": card.name,
            "color": COLOR_NEW_CARD,
            "fields": fields,
            "footer": {"text": bank_name},
        }
        if card.apply_url:
            embed["url"] = card.apply_url
        discord_embeds.append(embed)

    return {"telegram": telegram_text, "discord_embeds": discord_embeds}


def format_price_drop_alert(
    product,
    snapshot,
    top_cards: list,
    is_target_reached: bool = False,
) -> dict:
    """格式化降價或目標價通知（含 Top 3 最佳結帳卡）"""
    emoji = "🎯" if is_target_reached else "📉"
    title = "目標價達成！" if is_target_reached else "價格警示"
    platform_name = "PChome" if product.platform == "pchome" else "Momo"

    discount_text = ""
    if snapshot.original_price and snapshot.original_price > snapshot.price:
        pct = round(snapshot.price / snapshot.original_price * 100)
        discount_text = f"（折 {pct} 折）"

    card_lines = "\n".join(
        f"  {i + 1}. {r['card'].name}：回饋 {r['best_rate']}% = "
        f"-${r['reward_amount']:.0f}，實付 ${snapshot.price - r['reward_amount']:.0f}"
        for i, r in enumerate(top_cards)
    )

    telegram_text = (
        f"{emoji} {title}：{product.name}\n\n"
        f"🏪 {platform_name} 現價：${snapshot.price:,}{discount_text}\n\n"
        f"💳 最佳結帳方式：\n{card_lines}\n\n"
        f"🔗 {product.url}"
    )

    embed = {
        "title": f"{emoji} {title}：{product.name}",
        "color": 0x00B894 if is_target_reached else 0xE17055,
        "fields": [
            {
                "name": f"🏪 {platform_name} 現價",
                "value": f"**${snapshot.price:,}**{discount_text}",
                "inline": True,
            },
            {
                "name": "💳 最佳結帳卡",
                "value": "\n".join(
                    f"{i + 1}. {r['card'].name} (-${r['reward_amount']:.0f})"
                    for i, r in enumerate(top_cards)
                ),
                "inline": False,
            },
        ],
        "url": product.url,
    }

    return {"telegram": telegram_text, "discord_embeds": [embed]}
