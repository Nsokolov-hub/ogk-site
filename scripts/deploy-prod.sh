#!/usr/bin/env bash
# Выкатка сайта на прод одной командой, с машины разработчика (scripts/deploy.sh — для запуска на самом сервере,
# но там нет Docker Hub и npm: его `build --pull` и сборка админки в образе Caddy не проходят).
#
#   ./scripts/deploy-prod.sh           выкатить origin/main на прод
#   ./scripts/deploy-prod.sh --admin   пересобрать админку, даже если admin/ не менялась
#   ./scripts/deploy-prod.sh --check   только проверить: что на проде, что уйдёт, есть ли связь
#
# Шаги: проверки (ветка main, всё закоммичено и запушено) → админка собирается здесь, если менялась → бэкап на
# сервере → код до origin/main → текущие образы помечаются rollback-<коммит> → сборка api, worker, migrate, web
# (без --pull) → образ Caddy с новой админкой → compose up → перезапуск Caddy, если менялся deploy/caddy
# → проверки (миграции, страницы, админка, CRM) → старые rollback-образы удаляются, кроме трёх последних.
# Откат печатается в конце.
set -euo pipefail

HOST=${SITE_DEPLOY_HOST:-kpuser@185.237.186.58}
KEY=${SITE_DEPLOY_KEY:-$HOME/.ssh/crm_deploy}
APP=${SITE_DEPLOY_DIR:-ogk-site}
SITE_URL=${SITE_DEPLOY_URL:-https://www.ogk-chem.ru}
ADMIN_URL=${SITE_DEPLOY_ADMIN_URL:-https://admin.ogk-chem.ru}
CRM_URL=${SITE_DEPLOY_CRM_URL:-https://crm.ogk-chem.ru}
SERVICES=(api worker migrate web)
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

step "Миграции и перезапуск"
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

step "Уборка старых образов отката (остаются три последних)"
remote "for repo in ${SERVICES[*]/#/ogk-site-} ogk-site-caddy; do docker images \$repo --format '{{.CreatedAt}}|{{.Tag}}' | grep '|rollback-' | sort -r | tail -n +4 | cut -d'|' -f2 | while read -r tag; do docker rmi -f \$repo:\$tag >/dev/null; done; done; docker image prune -f >/dev/null; df -h / | tail -1"

cat <<EOF

ГОТОВО: на проде $sha (было $live).
Откат, если понадобится (если в выкатке была миграция базы, сначала откатите её):
  ssh $HOST 'cd $APP && for s in ${SERVICES[*]}; do docker tag ogk-site-\$s:rollback-$live ogk-site-\$s:latest; done && docker tag ogk-site-caddy:rollback-$live ogk-site-caddy:local && source scripts/lib.sh && compose up -d --no-build'
EOF
