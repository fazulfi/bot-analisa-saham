# systemd deployment

Gunakan systemd (bukan cron) untuk mode produksi:

1. Copy unit files:
   - `bot-analisa-watch.service`
   - `bot-analisa-generate.service`
   - `bot-analisa-generate.timer`
2. Sesuaikan path `WorkingDirectory`, `PYTHONPATH`, ticker list, dan binary python.
3. Reload daemon:
   ```bash
   sudo systemctl daemon-reload
   ```
4. Enable + start watcher:
   ```bash
   sudo systemctl enable --now bot-analisa-watch.service
   ```
5. Enable + start timer:
   ```bash
   sudo systemctl enable --now bot-analisa-generate.timer
   ```
6. Pastikan timezone server `Asia/Jakarta`.
