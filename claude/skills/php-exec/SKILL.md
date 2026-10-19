---
name: php-exec
description: >-
  Execute PHP/Laravel commands inside the Podman PHP-FPM container from host.
  Use when needing to run artisan, composer, phpunit, or any PHP command.
  Triggers on: php artisan, composer, phpunit, tinker, migrate, seed, test.
---

# PHP Container Command Executor

Execute PHP/Laravel commands inside the Podman `php-fpm` container via `podman exec`, bridging host Claude Code to containerized PHP runtime.

Host does NOT have PHP/Composer installed — all PHP commands MUST go through the container. Node.js (v22) is the opposite: runs directly on host, no `podman exec` needed.

## Containers

- `php-fpm`: PHP 8.4 + Composer only. No AI tools, no Node.js.
- `nginx`: reverse proxy, talks to PHP-FPM via Unix socket.
- `mariadb`: dev database, port 3306.
- `redis`: cache, port 6379.
- Podman VM: ~3.7GB RAM, 6 CPUs; containers have mem_limit enforced.

## Path Mapping

Host `~/code/php/` is mounted under container `/var/www/html/`. The exact
mapping differs per machine (some map `~/code/php/{path}` → `/var/www/html/{path}`,
others → `/var/www/html/php/{path}`). Don't guess — check once:

```bash
podman inspect php-fpm --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

## Execution Pattern

```bash
# PHP (container)
podman exec -w /var/www/html/<project> php-fpm <command>

# Interactive (tinker)
podman exec -it -w /var/www/html/<project> php-fpm php artisan tinker

# Node.js (host direct)
cd ~/code/php/<project> && npm <command>
```

## Common Tasks

| Task | Command |
|------|---------|
| Artisan | `podman exec -w /var/www/html/{project} php-fpm php artisan {cmd}` |
| Composer | `podman exec -w /var/www/html/{project} php-fpm composer {cmd}` |
| Tests | `podman exec -w /var/www/html/{project} php-fpm php artisan test` |
| Fresh migrate | `podman exec -w /var/www/html/{project} php-fpm php artisan migrate:fresh --seed` |
| Vite dev | `cd ~/code/php/{project} && npm run dev` |
| Vite build | `cd ~/code/php/{project} && npm run build` |

## Gotchas

- herdr agent sessions sandbox `$HOME` — prefix podman commands with
  `HOME=<real home>` (e.g. `HOME=/Users/huai-chitzeng`) or they fail with
  "Cannot connect to Podman".
- Piping stdin into `podman exec` (heredoc) needs `-i`, otherwise the target
  file is silently created empty.
- Never inline PHP containing `=>` on the command line (`tinker --execute=`,
  `php -r`): a quoting slip turns `=>` into a shell `>` redirect and leaves
  stray empty files (`null`, `true\`, …) in the project root. Pipe it via a
  quoted heredoc: `podman exec -i -w ... php-fpm php artisan tinker <<'PHP' ... PHP`.
- Interactive commands (tinker) need `-it`.
- Permission error → add `--user root`.

## Container Management

Compose file: `~/srv/servers/docker-compose.yml` (older machines: `~/podman`).

- Start: `cd ~/srv/servers && podman-compose up -d`
- Stop: `cd ~/srv/servers && podman-compose down`
- Rebuild: `cd ~/srv/servers && podman-compose up -d --build`
- Stats: `podman stats --no-stream`

## MariaDB

- Host: `127.0.0.1:3306`, root / `1qaz@WSX`
- From containers: `mariadb:3306` (Laravel `.env`: `DB_HOST=mariadb`)
- `DB_CONNECTION=mariadb` (Laravel 11+, NOT mysql)
- Backup: `podman exec mariadb mariadb-dump -u root -p'1qaz@WSX' --all-databases`
