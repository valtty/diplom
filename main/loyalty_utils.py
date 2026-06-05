"""Настройки и начисление бонусов программы лояльности."""

from decimal import Decimal

from .models import BonusTransaction, LoyaltySettings


def get_loyalty_settings() -> LoyaltySettings:
    settings_obj = LoyaltySettings.objects.first()
    if settings_obj is None:
        settings_obj = LoyaltySettings.objects.create(
            bonus_percent=Decimal("10.00"),
            bonus_to_rub_rate=Decimal("1.00"),
            welcome_bonus=500,
            referral_bonus=200,
            is_active=True,
        )
    return settings_obj


def accrue_welcome_bonus(user, client) -> int:
    """Приветственные бонусы при регистрации. Возвращает начисленную сумму."""
    loyalty = get_loyalty_settings()
    if not loyalty.is_active or not loyalty.welcome_bonus:
        return 0
    if BonusTransaction.objects.filter(user=user, source="welcome").exists():
        return 0
    client.bonus_balance += loyalty.welcome_bonus
    client.save(update_fields=["bonus_balance"])
    BonusTransaction.objects.create(
        user=user,
        amount=loyalty.welcome_bonus,
        type="accrual",
        source="welcome",
        description="Приветственные бонусы при регистрации",
    )
    return loyalty.welcome_bonus


def accrue_completion_bonus(appointment) -> int:
    """Бонусы клиенту после выполненной процедуры. Возвращает начисленную сумму."""
    loyalty = get_loyalty_settings()
    if not loyalty.is_active:
        return 0
    if BonusTransaction.objects.filter(
        appointment=appointment,
        type="accrual",
        source="appointment",
    ).exists():
        return 0
    bonus_amount = int(appointment.service.price * (loyalty.bonus_percent / Decimal("100")))
    if bonus_amount <= 0:
        return 0
    client = appointment.client
    client.bonus_balance += bonus_amount
    client.save(update_fields=["bonus_balance"])
    BonusTransaction.objects.create(
        user=client.user,
        amount=bonus_amount,
        type="accrual",
        source="appointment",
        appointment=appointment,
        description="Начисление за выполненную процедуру",
    )
    return bonus_amount
