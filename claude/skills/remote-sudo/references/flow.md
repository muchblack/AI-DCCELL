## 步驟

1. 列白名單（不會卡密碼提示）：
   `ssh -o BatchMode=yes -o ConnectTimeout=5 {host} "sudo -n -l"`

2. 若帶 `--cmd`，額外測試該指令：
   `ssh -o BatchMode=yes -o ConnectTimeout=5 {host} "sudo -n {cmd} && echo PASSWORDLESS_OK || echo NEEDS_PASSWORD"`

3. 回報時務必說明：這是「精確指令匹配」的白名單，不代表整個 sudo 免密碼——
   一條 `NOPASSWD:/usr/bin/su` 不等於 `sudo -n true` 也會過。

## 備註

- `myMini`（內網 192.168.0.103）與 `myMini-outside`（外網 114.32.45.44:2222）是同一台實體機器，
  只是內外網 IP 不同，白名單內容一致，不需要分別查兩次。
- host 未指定時預設查 `myMini`。
