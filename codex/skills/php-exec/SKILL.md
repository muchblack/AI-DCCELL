---
name: php-exec
description: >-
  Execute PHP/Laravel commands inside the Podman PHP-FPM container from host.
  Use when needing to run artisan, composer, phpunit, or any PHP command.
  Triggers on: php artisan, composer, phpunit, tinker, migrate, seed, test.
---

# PHP Container Command Executor

Execute PHP/Laravel commands inside the Podman `php-fpm` container
via `podman exec`, bridging host Claude Code to containerized PHP runtime.

## When to Use

Automatically trigger when the task requires:
- `php artisan` commands (migrate, tinker, make:*, queue, schedule)
- `composer` commands (install, require, update, dump-autoload)
- `phpunit` / `php artisan test` / Pest
- Any PHP script execution

**NOT for npm/yarn** — Node.js commands run directly on host, no podman exec needed.

## Container Details

- Container name: `php-fpm`
- Working directory: `/var/www/html/php` (maps to host `/Users/vincenttseng/code`)
- PHP version: 8.4

## Execution Pattern

PHP commands via container:
```bash
podman exec -w /var/www/html/php/<path-to-project> php-fpm <command>
```

Node.js commands directly on host:
```bash
cd /Users/vincenttseng/code/php/<path-to-project> && npm <command>
```

## Common Commands Reference

### PHP (Container via podman exec)

| Task | Command |
|------|---------|
| Artisan | `podman exec -w /var/www/html/php/{project} php-fpm php artisan {cmd}` |
| Composer Install | `podman exec -w /var/www/html/php/{project} php-fpm composer install` |
| Composer Require | `podman exec -w /var/www/html/php/{project} php-fpm composer require {pkg}` |
| Run Tests | `podman exec -w /var/www/html/php/{project} php-fpm php artisan test` |
| Tinker | `podman exec -it -w /var/www/html/php/{project} php-fpm php artisan tinker` |
| Fresh Migrate | `podman exec -w /var/www/html/php/{project} php-fpm php artisan migrate:fresh --seed` |

### Node.js (Host Direct)

| Task | Command |
|------|---------|
| NPM Install | `cd ~/code/php/{project} && npm install` |
| Vite Dev | `cd ~/code/php/{project} && npm run dev` |
| Vite Build | `cd ~/code/php/{project} && npm run build` |

## Path Mapping

Host path `/Users/vincenttseng/code/php/` maps to container `/var/www/html/php/`.

When user references a file at `/Users/vincenttseng/code/php/my/twcamp/`,
the container path is `/var/www/html/php/my/twcamp/`.

## Error Handling

- If container is not running: suggest `cd ~/podman && podman-compose up -d`
- If command fails with permission error: add `--user root` to podman exec
- For interactive commands (tinker): use `-it` flag
