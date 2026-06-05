"""Проверка полей демо-оплаты картой (длина номера, срок, CVV, имя — без Luhn)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import List, Tuple


def validate_card_payment(
    card_number: str,
    expiry: str,
    cvv: str,
    cardholder: str,
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    pan = "".join(c for c in (card_number or "") if c.isdigit())
    if len(pan) < 16 or len(pan) > 19:
        errors.append("Номер карты: введите от 16 до 19 цифр.")

    exp = (expiry or "").strip().replace(" ", "")
    if len(exp) != 5 or exp[2] != "/":
        errors.append("Срок: укажите в формате MM/YY.")
    else:
        mm_s, yy_s = exp[:2], exp[3:]
        if not mm_s.isdigit() or not yy_s.isdigit():
            errors.append("Срок: только цифры в формате MM/YY.")
        else:
            mm, yy = int(mm_s), int(yy_s)
            if mm < 1 or mm > 12:
                errors.append("Срок: месяц от 01 до 12.")
            else:
                y_full = 2000 + yy if yy < 100 else yy
                last = monthrange(y_full, mm)[1]
                exp_end = date(y_full, mm, last)
                if exp_end < date.today():
                    errors.append("Срок: карта просрочена.")

    cvv_digits = "".join(c for c in (cvv or "") if c.isdigit())
    if len(cvv_digits) not in (3, 4):
        errors.append("CVV: введите 3 или 4 цифры.")

    name = (cardholder or "").strip()
    if len(name) < 2:
        errors.append("Имя держателя: укажите как на карте.")

    return (len(errors) == 0, errors)
