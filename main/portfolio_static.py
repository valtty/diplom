"""Статические изображения блока портфолио на главной (img/portfolio1…7)."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.templatetags.static import static


def home_portfolio_image_urls() -> list[str]:
    """
    Возвращает 7 URL для {% static %} — первый найденный файл среди расширений.
    Порядок: portfolio1 … portfolio7 (слева направо, сверху вниз в вёрстке).
    """
    static_dir = Path(settings.BASE_DIR) / "static" / "img"
    exts = (".webp", ".png", ".jpg", ".jpeg", ".gif")
    urls: list[str] = []
    for i in range(1, 8):
        found = False
        for ext in exts:
            rel = f"img/portfolio{i}{ext}"
            if (static_dir / f"portfolio{i}{ext}").is_file():
                urls.append(static(rel))
                found = True
                break
        if not found:
            urls.append(static(f"img/portfolio{i}.png"))
    return urls
