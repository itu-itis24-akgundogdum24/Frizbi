"""
Teshis log modulu.
main.py'nin yaninda durur ve sistemin her asamasini diagnostic.log
dosyasina yazar. Dosya her calistirmada sifirlanir.

Kullanim (main.py icinde):
    from diagnostic import diag, reset_diagnostic_log, diag_section

    reset_diagnostic_log()              # program basinda bir kez
    diag("AGENT", "trend_agent basladi")
    diag("NETWORK", "Reddit istegi", url=url, status=200, ok=True)
    diag("ERROR", "scrape basarisiz", exc=e)
"""

import traceback
from datetime import datetime

DIAGNOSTIC_FILE = "diagnostic.log"


def reset_diagnostic_log() -> None:
    """Teshis dosyasini sifirlar; her yeni calistirmada bir kez cagrilir."""
    with open(DIAGNOSTIC_FILE, "w", encoding="utf-8") as f:
        f.write("Teshis Log Dosyasi\n")
        f.write(f"Calistirma baslangici: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n")


def _timestamp() -> str:
    """Milisaniye hassasiyetinde zaman damgasi doner."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def diag(event_type: str, message: str, **fields) -> None:
    """
    Teshis dosyasina tek satir yazar.
    event_type: olay turu (AGENT, NETWORK, SCRAPE, RETRY, ERROR, FLOW, DATA, LLM).
    message: kisa aciklama.
    fields: opsiyonel anahtar-deger detaylar (url, status, attempt, ok, exc vb.).
    """
    parts = [f"[{_timestamp()}]", f"[{event_type:<8}]", message]

    for key, value in fields.items():
        if key == "exc" and value is not None:
            # Istisna nesnesi ozel islenir: tur ve mesaj yazilir
            parts.append(f"| exc={type(value).__name__}: {value}")
        else:
            parts.append(f"| {key}={value}")

    line = " ".join(parts)

    with open(DIAGNOSTIC_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    # Terminalde de anlik gorunur
    print(line)


def diag_section(title: str) -> None:
    """Teshis dosyasina gorsel bir bolum ayraci yazar."""
    line = f"\n----- {title} -----"
    with open(DIAGNOSTIC_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def diag_exception(event_type: str, message: str, exc: Exception) -> None:
    """
    Bir istisnayi tam traceback ile teshis dosyasina yazar.
    Sistemin nerede boguldugunu ayrintili gormek icin kullanilir.
    """
    diag(event_type, message, exc=exc)
    tb = traceback.format_exc()
    with open(DIAGNOSTIC_FILE, "a", encoding="utf-8") as f:
        f.write("  --- Traceback ---\n")
        for tb_line in tb.splitlines():
            f.write(f"  {tb_line}\n")
        f.write("  --- Traceback sonu ---\n")
