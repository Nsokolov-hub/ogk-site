#!/usr/bin/env bash
# Выкатка сайта на прод одной командой, с машины разработчика (scripts/deploy.sh — для запуска на самом сервере,
# но там нет Docker Hub и npm: его `build --pull` и сборка админки в образе Caddy не проходят).
#
#   ./scripts/deploy-prod.sh           выкатить origin/main на прод
#   ./scripts/deploy-prod.sh --admin   пересобрать админку, даже если admin/ не менялась
#   ./scripts/deploy-prod.sh --check   только проверить: что на проде, что уйдёт, есть ли связь
#   SITE_DEPLOY_WATCH=300 ./scripts/deploy-prod.sh   наблюдать после выкатки 300 с (по умолчанию 180, 0 — не наблюдать)
#
# Шаги: проверки (ветка main, всё закоммичено и запушено) → админка собирается здесь, если менялась → бэкап на
# сервере → код до origin/main → текущие образы помечаются rollback-<коммит> → сборка api, worker, migrate, web
# (без --pull) → образ Caddy с новой админкой → пауза, пока сервер остынет после сборки → compose up → перезапуск
# Caddy, если менялся deploy/caddy → проверки (миграции, страницы, админка, CRM) → наблюдение: ошибки API на живом
# трафике и время ответа страниц; при сбое — автоматический откат на прежние образы → старые rollback-образы
# удаляются, кроме трёх последних. Откат печатается в конце.
set -euo pipefail

HOST=${SITE_DEPLOY_HOST:-kpuser@185.237.186.58}
KEY=${SITE_DEPLOY_KEY:-$HOME/.ssh/crm_deploy}
APP=${SITE_DEPLOY_DIR:-ogk-site}
SITE_URL=${SITE_DEPLOY_URL:-https://www.ogk-chem.ru}
ADMIN_URL=${SITE_DEPLOY_ADMIN_URL:-https://admin.ogk-chem.ru}
CRM_URL=${SITE_DEPLOY_CRM_URL:-https://crm.ogk-chem.ru}
SERVICES=(api worker migrate web)
WATCH=${SITE_DEPLOY_WATCH:-180}
SSH=(ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o ServerAliveInterval=10 "$HOST")

step() { printf '\n== %s\n' "$*"; }
die() { printf '\nОШИБКА: %s\n' "$*" >&2; exit 1; }
# A script for bash on the server, in the site's folder, with compose() and env_value() of scripts/lib.sh.
remote() { "${SSH[@]}" "cd $APP && bash -s" <<<"source scripts/lib.sh >/dev/null; $1"; }

# Long jobs run detached on the server: a silent ssh session gets cut. Waits for "EXIT:<code>" in the log.
remote_job() {
  local name=$1 command=$2 log="/tmp/site-deploy-$1.log"
  remote "rm -f $log; (setsid nohup bash -c 'source scripts/lib.sh >/dev/null; $command; echo EXIT:\$?' > $log 2>&1 < /dev/null &)"
  local waited=0 status
  while :; do
    sleep 10
    waited=$((waited + 10))
    status=$(remote "grep -o 'EXIT:[0-9]*' $log | tail -1" || true)
    if [[ -n $status ]]; then
      remote "tail -5 $log" || true
      [[ $status == EXIT:0 ]] || die "$name завершился с ошибкой ($status), журнал на сервере: $log"
      return
    fi
    ((waited % 60 == 0)) && echo "… $name идёт ${waited} с"
    ((waited < 2700)) || die "$name идёт дольше 45 минут, журнал на сервере: $log"
  done
}

mode=deploy
admin=""
for arg in "$@"; do
  case "$arg" in
    --check) mode=check ;;
    --admin) admin=1 ;;
    *) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
  esac
done

cd "$(git rev-parse --show-toplevel)"
step "Проверки"
[[ $(git rev-parse --abbrev-ref HEAD) == main ]] || die "выкатывается только ветка main"
git diff --quiet && git diff --cached --quiet || die "есть незакоммиченные изменения в отслеживаемых файлах"
git fetch -q origin main
[[ $(git rev-parse HEAD) == $(git rev-parse origin/main) ]] || die "локальный main не совпадает с origin/main: запушьте или подтяните"
sha=$(git rev-parse --short HEAD)
live=$(remote "git rev-parse --short HEAD") || die "нет связи с сервером $HOST"
echo "На проде: $live · выкатываем: $sha"
git log --oneline "$live..$sha" 2>/dev/null | sed 's/^/  /' || true
if [[ -z $admin ]] && ! git diff --quiet "$live" "$sha" -- admin deploy/caddy.Dockerfile 2>/dev/null; then admin=1; fi
if [[ -n $admin ]]; then echo "Админка: пересобирается"; else echo "Админка: без изменений"; fi
migrations=$(git diff --name-only "$live" "$sha" -- backend/alembic/versions 2>/dev/null | sed 's/^/  /' || true)
[[ -z $migrations ]] || printf 'Новые миграции:\n%s\n' "$migrations"
remote "compose ps --format '{{.Name}} {{.Status}}'" | sed 's/^/  /'
remote "df -h / | tail -1" | sed 's/^/  диск: /'
if [[ $mode == check ]]; then
  echo "Проверка закончена, ничего не менялось."
  exit 0
fi
[[ $live != "$sha" ]] || echo "Этот коммит уже на проде: пересобираю и перезапускаю."

admin_bundle=""
if [[ -n $admin ]]; then
  step "Сборка админки здесь"
  (cd admin && npm run build >/dev/null)
  admin_bundle=$(grep -o 'assets/index-[^"]*\.js' admin/dist/index.html | head -1)
  [[ -n $admin_bundle ]] || die "в собранном admin/dist/index.html нет основного скрипта"
fi

step "Бэкап на сервере"
remote_job backup "./scripts/backup.sh"

step "Код до origin/main, образы для отката: rollback-$live"
remote "git fetch -q origin && git merge --ff-only origin/main && git log --oneline -1"
remote "for s in ${SERVICES[*]}; do docker tag ogk-site-\$s:latest ogk-site-\$s:rollback-$live; done; docker tag ogk-site-caddy:local ogk-site-caddy:rollback-$live"

step "Сборка ${SERVICES[*]} (без --pull: Docker Hub с сервера недоступен)"
remote_job build "compose build ${SERVICES[*]}"

if [[ -n $admin ]]; then
  step "Образ Caddy с новой админкой"
  tmp=/tmp/site-caddy-$sha
  tar czf - -C admin dist | "${SSH[@]}" "rm -rf $tmp && mkdir -p $tmp && tar xzf - -C $tmp && mv $tmp/dist $tmp/admin-dist"
  # The runtime stage of deploy/caddy.Dockerfile, with the admin panel built here instead of in a node stage.
  { grep '^FROM caddy' deploy/caddy.Dockerfile; echo 'COPY admin-dist /srv/admin'; } | "${SSH[@]}" "cat > $tmp/Dockerfile"
  remote_job caddy "docker build -q -t ogk-site-caddy:local $tmp && rm -rf $tmp"
fi

# Сборка занимает все ядра сервера, а сайт в это время работает. Новые контейнеры стартуют с пустыми кэшами, и первая
# волна запросов на нагруженный сервер — то, с чего начался сбой 12.11.2026. Ждём, пока нагрузка спадёт, до 3 минут.
step "Пауза: нагрузка сервера после сборки"
for _ in $(seq 1 18); do
  read -r load cores < <(remote 'echo "$(cut -d" " -f1 /proc/loadavg) $(nproc)"')
  LC_ALL=C awk -v l="$load" -v c="$cores" 'BEGIN { exit !(l < c) }' && break
  echo "  нагрузка $load на $cores ядра — ждём"
  sleep 10
done
echo "  нагрузка $load на $cores ядра"

step "Миграции и перезапуск"
up_at=$(remote "date -u +%Y-%m-%dT%H:%M:%SZ")
remote_job up "compose up -d --no-build"

# deploy/caddy is mounted into the running Caddy, so a changed config needs a restart (a new admin image already
# recreated the container with it). The production Caddyfile has `admin off`, so `caddy reload` cannot reach it:
# validate inside the container first, then restart — the site, the admin panel and the CRM pause for seconds.
if [[ -z $admin ]] && ! git diff --quiet "$live" "$sha" -- deploy/caddy 2>/dev/null; then
  step "Конфиг Caddy изменился: проверка и перезапуск Caddy (несколько секунд)"
  remote "compose exec -T caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -1" |
    grep -q 'Valid configuration' || die "Caddy не принимает новый конфиг: работает прежний, см. compose exec caddy caddy validate"
  remote "compose restart caddy 2>&1 | tail -1"
fi

step "Проверки после выкатки"
remote "compose ps -a migrate --format '{{.State}} {{.ExitCode}}'" | grep -q 'exited 0' || die "миграции не завершились успешно: compose logs migrate"
current=$(remote "compose exec -T api alembic current 2>/dev/null | tail -1")
heads=$(remote "compose exec -T api alembic heads 2>/dev/null | tail -1")
echo "alembic: $current (последняя: $heads)"
[[ ${current%% *} == "${heads%% *}" ]] || die "база не на последней миграции"
for url in "$SITE_URL/" "$ADMIN_URL/" "$CRM_URL/ready"; do
  for _ in $(seq 1 30); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "$url" || true)
    [[ $code == 200 ]] && break
    sleep 5
  done
  [[ $code == 200 ]] || die "$url отвечает $code"
  echo "$url: 200"
done
if [[ -n $admin_bundle ]]; then
  curl -s "$ADMIN_URL/" | grep -q "$admin_bundle" || die "админка отдаёт не новую сборку (ждали $admin_bundle)"
  echo "админка: $admin_bundle"
fi
remote "compose ps --format '{{.Name}} {{.Status}}'" | sed 's/^/  /'

# Откат на образы rollback-$live, когда наблюдение увидело сбой. С миграциями базы — только вручную: прежний код на
# новой схеме может не заработать, а откат миграции требует решения.
rollback() {
  step "АВТОМАТИЧЕСКИЙ ОТКАТ на $live: $1"
  [[ -z $migrations ]] || die "в выкатке есть миграции базы — автоматически не откатываю, на проде остаётся $sha. Откатите миграцию, затем образы: for s in ${SERVICES[*]}; do docker tag ogk-site-\$s:rollback-$live ogk-site-\$s:latest; done; compose up -d --no-build"
  remote "for s in ${SERVICES[*]}; do docker tag ogk-site-\$s:rollback-$live ogk-site-\$s:latest; done; docker tag ogk-site-caddy:rollback-$live ogk-site-caddy:local"
  remote_job rollback "compose up -d --no-build"
  # The checkout follows what runs, so --check and the next deploy see $live; the next deploy fast-forwards again.
  remote "git reset -q --keep $live && git log --oneline -1 || echo 'код на сервере остался на $sha'" || true
  if ! git diff --quiet "$live" "$sha" -- deploy/caddy 2>/dev/null; then
    remote "compose restart caddy 2>&1 | tail -1" || true
  fi
  for _ in $(seq 1 30); do
    code=$(curl -s -o /dev/null -m 20 -w '%{http_code}' "$SITE_URL/" || true)
    [[ $code == 200 ]] && break
    sleep 5
  done
  remote "compose ps --format '{{.Name}} {{.Status}}'" | sed 's/^/  /'
  die "выкатка $sha не прошла наблюдение ($1), на проде снова $live (сайт отвечает $code). Журнал API: compose logs --since $up_at api"
}

# Наблюдение на живом трафике: доля ответов API 5xx (в том числе 503 защиты от перегрузки) и время ответа страниц —
# главной, каталога, карточки товара и страницы вещества. Сбой — откат.
if ((WATCH > 0)); then
  step "Наблюдение ${WATCH} с: ошибки API и время ответа страниц, при сбое — автоматический откат"
  sample=$(curl -s -m 10 "$SITE_URL/api/v1/public/catalog/popular?limit=1&lang=ru&sort=popular" |
    python3 -c 'import json, sys; i = json.load(sys.stdin)["items"][0]; print(i["slug"], i.get("cas") or "")' 2>/dev/null || true)
  read -r product cas <<<"$sample"
  probes=("$SITE_URL/" "$SITE_URL/catalog/")
  [[ -z ${product:-} ]] || probes+=("$SITE_URL/product/$product/")
  [[ -z ${cas:-} ]] || probes+=("$SITE_URL/cas/$cas/")
  started=$SECONDS bad_rounds=0
  while ((SECONDS - started < WATCH)); do
    sleep 15
    lines=$(remote "compose logs --no-log-prefix --since $up_at api 2>/dev/null | grep -F '\"event\": \"http_request\"' | grep -vF '\"route\": \"/ready\"'" || true)
    total=$(grep -c . <<<"$lines" || true)
    errors=$(grep -cE '"status": 5[0-9]{2}' <<<"$lines" || true)
    shed=$(grep -cF '"route": "overloaded"' <<<"$lines" || true)
    p95=$(grep -oE '"duration_ms": [0-9.]+' <<<"$lines" | awk '{print $2}' | LC_ALL=C sort -n |
      LC_ALL=C awk '{v[NR] = $1} END {i = int(NR * 0.95); if (i < 1) i = NR; printf "%d", (NR ? v[i] : 0)}')
    report="" failed=""
    for url in "${probes[@]}"; do
      read -r code took < <(curl -s -o /dev/null -m 20 -w '%{http_code} %{time_total}\n' "$url" || echo "000 20")
      report+=" $code/$(LC_ALL=C printf '%.1f' "$took")с"
      [[ $code == 200 ]] || failed=1
    done
    printf '  %3d с · API: %d запросов, 5xx %d (из них отказов перегрузки %d), p95 %d мс · страницы:%s\n' \
      $((SECONDS - started)) "$total" "$errors" "$shed" "$p95" "$report"
    if ((errors >= 20 && errors * 100 >= total * 5)); then
      rollback "API: $errors ответов 5xx из $total"
    fi
    if [[ -n $failed ]]; then bad_rounds=$((bad_rounds + 1)); else bad_rounds=0; fi
    ((bad_rounds < 3)) || rollback "страницы сайта не отвечают 200 три проверки подряд"
  done
  echo "Наблюдение пройдено."
fi

step "Уборка старых образов отката (остаются три последних)"
remote "for repo in ${SERVICES[*]/#/ogk-site-} ogk-site-caddy; do docker images \$repo --format '{{.CreatedAt}}|{{.Tag}}' | grep '|rollback-' | sort -r | tail -n +4 | cut -d'|' -f2 | while read -r tag; do docker rmi -f \$repo:\$tag >/dev/null; done; done; docker image prune -f >/dev/null; df -h / | tail -1"

cat <<EOF

ГОТОВО: на проде $sha (было $live).
Откат, если понадобится (если в выкатке была миграция базы, сначала откатите её):
  ssh $HOST 'cd $APP && for s in ${SERVICES[*]}; do docker tag ogk-site-\$s:rollback-$live ogk-site-\$s:latest; done && docker tag ogk-site-caddy:rollback-$live ogk-site-caddy:local && source scripts/lib.sh && compose up -d --no-build'
EOF
