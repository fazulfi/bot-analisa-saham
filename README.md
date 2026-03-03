# Bot Analisa Saham (Indonesia)

Bot analisa saham dengan workflow production-ish:

- Market data cache: `data/<TICKER>.csv`
- Signal source of truth: `signals/signals.db` (SQLite)
- EOD generation: `bot_analisa.cli.generate_signals`
- Watcher TP/SL: `bot_analisa.cli.watch_signals`
- Legacy CSV migration: `bot_analisa.cli.migrate_signals`

## Struktur utama
- `src/bot_analisa/data` -> provider + cleaner
- `src/bot_analisa/indicators` -> indikator teknikal
- `src/bot_analisa/strategy` -> logika signal
- `src/bot_analisa/signals` -> SQLite storage + watcher
- `src/bot_analisa/cli` -> entrypoint operasional

## Command penting
### 1) Migrasi CSV signals lama (sekali)
```bash
python -m bot_analisa.cli.migrate_signals --signals-folder signals
```

### 2) Generate signal EOD (latest bar only)
```bash
python -m bot_analisa.cli.generate_signals BBCA.JK BBRI.JK --period 1y --interval 1d --data-folder data --signals-folder signals
```

### 3) Watcher loop
```bash
python -m bot_analisa.cli.watch_signals --loop --interval 300 --data-folder data --signals-folder signals
```

## Deploy systemd
Lihat `docs/systemd/` untuk contoh unit service + timer.
