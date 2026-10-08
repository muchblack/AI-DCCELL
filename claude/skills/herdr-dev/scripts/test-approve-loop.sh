#!/usr/bin/env bash
# approve-loop.sh 白名單的回歸測試：bash scripts/test-approve-loop.sh
# 只載入判斷函式，不會呼叫 herdr。
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
WT=/tmp/proj/.herdr-dev/worktrees/worker-x
P='podman exec -w /x cashier-php '
PREFIX="$P"
eval "$(sed -n '/^dangerous() {/,/^for _ in/p' "$DIR/approve-loop.sh" | sed '$d')"
fail=0
t(){ if allowed "$2"; then r=allow; else r=stop; fi
     [ "$r" = "$1" ] || { echo "FAIL want $1 got $r: $2"; fail=1; }; }
# 還原例外
t allow 'git checkout -- public/'
t allow 'git checkout -- public'
t allow 'git checkout -- public/ && git status --short'
t allow "git -C $WT checkout -- public/"
t allow "cd $WT && git checkout -- public/ && git status --short"
t stop  'git checkout main'
t stop  'git checkout -- public/ app/'
t stop  'git checkout -- .'
t stop  'git -C /tmp/other checkout -- public/'
t stop  'cd /tmp/other && git checkout -- public/'
t stop  'git checkout -- public/ && git push'
t stop  'git checkout -- public/ && herdr agent list'
# 歷史實際放行過的指令
t allow 'git add app/Models/User.php app/Models/Event.php'
t allow "git diff --check && git add app/Http/Controllers/ItemController.php routes/api.php && git commit -m '新增場次可售商品 API'"
t allow "git diff --check && git add app/Filament/Resources/ItemResource.php tests/Feature/ItemResourceTest.php && git commit -m '區分管理者商品篩選選項擁有者'"
t allow 'git status --short'
t allow 'podman exec -w /x cashier-php php artisan test --filter=ItemResourceTest'
t allow "git -C $WT log -1"
t allow "cd $WT && git status"
# ; 弱點與其他夾帶
t stop  'git status; python3 x.py'
t stop  'git status ; rm x'
t stop  'git status & python3 x.py'
t stop  'git status | sh'
t stop  'git log > /etc/x'
t stop  'git show $(whoami)'
t stop  'git show `whoami`'
t stop  'podman exec -w /x cashier-php php artisan test; rm -rf ~'
t stop  'podman exec -w /x cashier-php php artisan test && curl x'
t stop  "git -C $WT status; rm x"
t stop  'git checkout -- public/; rm -rf app'
t stop  'git checkout -- public/ && rm -rf app'
t stop  "cd $WT; git status"
t stop  'python3 x.py'
[ $fail = 0 ] && echo "ALL PASS"; exit $fail
