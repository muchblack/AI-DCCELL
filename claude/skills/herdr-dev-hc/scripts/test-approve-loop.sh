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
# git -C <worktree> 不得繞過子指令白名單
t stop  "git -C $WT reset --hard HEAD~3"
t stop  "git -C $WT push origin main"
t stop  "git -C $WT clean -fdx"
t stop  "git -C $WT checkout main"
t stop  "git -C $WT config core.hooksPath /tmp/x"
t stop  "cd $WT && git -C $WT push"
t stop  'git diff --output=/home/u/.bashrc'
t stop  "git -C $WT log --output /tmp/x"
t stop  'podman exec -w /x cashier-php git -C /var/www push origin main'
t stop  'podman exec -w /x cashier-php git -c core.x=y -C /w reset --hard'
t allow "git -C $WT/ status"
t allow 'podman exec -w /x cashier-php git status'
t allow "git -C $WT diff --stat"
t allow "git -C $WT add app/X.php && git -C $WT commit -m x"
# codex 對話框把長指令折成多行：必須併回整條再判斷，不能只看 "$ " 那一行
e(){ got=$(printf '%b' "$2" | extract_cmd)
     [ "$got" = "$1" ] || { echo "FAIL extract want [$1] got [$got]"; fail=1; }; }
e 'bash run.sh /wt /logs/a.log tests/x.py' '  Reason: x\n\n  $ bash run.sh /wt\n  /logs/a.log tests/x.py\n\n› 1. Yes, proceed (y)\n'
e 'git status' '  $ git status\n\n› 1. Yes, proceed (y)\n'
e 'git status' '  $ old cmd\n\n  $ git status\n› 1. Yes, proceed (y)\n'
PREFIX="bash run.sh $WT "
t allow "$(printf '  $ bash run.sh %s\n  /logs/a.log tests/x.py\n\n' "$WT" | extract_cmd)"
t stop  "$(printf '  $ bash run.sh %s\n  /logs/a.log; rm -rf ~\n\n' "$WT" | extract_cmd)"
# 改檔確認框的 Destination
d(){ if edit_allowed "$2"; then r=allow; else r=stop; fi
     [ "$r" = "$1" ] || { echo "FAIL edit want $1 got $r: $2"; fail=1; }; }
d allow "$WT/claude/skills/x/scripts/pulse.py"
d allow "$WT/SKILL.md"
d allow /tmp/proj/.herdr-dev/tasks/slug-a/report.md
d stop  /tmp/proj/.herdr-dev/tasks/slug-a/verdict.md
d stop  /tmp/proj/.herdr-dev/tasks/slug-a/sub/report.md
d stop  /tmp/proj/.herdr-dev/tasks/report.md
d stop  /tmp/proj/.herdr-dev/state.json
d stop  "$WT/../worker-y/x.py"
d stop  "$WT/../../tasks/a/report.md"
d stop  "${WT}-evil/x.py"
d stop  /tmp/proj/app/x.php
d stop  /home/u/.bashrc
d stop  "claude/skills/x.py"
d stop  ""
[ $fail = 0 ] && echo "ALL PASS"; exit $fail
