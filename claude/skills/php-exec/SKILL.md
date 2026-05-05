---
name: php-exec
description: >-
  Execute PHP/Laravel commands inside the Podman PHP-FPM container from host.
  Use when needing to run artisan, composer, phpunit, or any PHP command.
  Triggers on: php artisan, composer, phpunit, tinker, migrate, seed, test.
---

# PHP Container Command Executor

Execute PHP/Laravel commands inside the Podman `php-fpm` container via `podman exec`, bridging host Claude Code to containerized PHP runtime.

Host does NOT have PHP/Composer installed — all PHP commands MUST go through the container. Node.js is the opposite: runs directly on host, no `podman exec` needed.

## Container Details

- Container: `php-fpm` (PHP 8.4)
- Host path `/Users/vincenttseng/code/php/` → container `/var/www/html/php/`

## Execution Pattern

```bash
# PHP (container)
podman exec -w /var/www/html/php/<project> php-fpm <command>

# Interactive (tinker)
podman exec -it -w /var/www/html/php/<project> php-fpm php artisan tinker

# Node.js (host direct)
cd /Users/vincenttseng/code/php/<project> && npm <command>
```

## Common Tasks

| Task | Command |
|------|---------|
| Artisan | `podman exec -w /var/www/html/php/{project} php-fpm php artisan {cmd}` |
| Composer | `podman exec -w /var/www/html/php/{project} php-fpm composer {cmd}` |
| Tests | `podman exec -w /var/www/html/php/{project} php-fpm php artisan test` |
| Fresh migrate | `podman exec -w /var/www/html/php/{project} php-fpm php artisan migrate:fresh --seed` |
| Vite dev | `cd ~/code/php/{project} && npm run dev` |
| Vite build | `cd ~/code/php/{project} && npm run build` |

## Error Handling

- Container not running → `cd ~/podman && podman-compose up -d`
- Permission error → add `--user root` to `podman exec`
- Interactive commands (tinker) → use `-it` flag
