#!/usr/bin/env bash
set -eu
repo=$1
evidence_dir=$2
demo=$(mktemp -d "$evidence_dir/demo.XXXXXX")
trap 'rm -rf "$demo"' EXIT
mkdir -p "$demo/home/state" "$demo/fakebin"
. "$repo/tests/lib.sh"
fm_write_meta "$demo/home/state/task.meta" "window=demo:fm-task" "kind=ship"
cat > "$demo/fakebin/tmux" <<'SH'
#!/usr/bin/env bash
case "${1:-}" in
  send-keys) exit 0 ;;
  display-message) case "$*" in *cursor_y*) printf '1\n';; *) printf 'fakepane\n';; esac ;;
  capture-pane) printf '╭────╮\n│    │\n╰────╯\n' ;;
esac
SH
cat > "$demo/fakebin/sleep" <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x "$demo/fakebin/tmux" "$demo/fakebin/sleep"
status="$demo/home/state/task.status"
printf 'needs-decision [key=grid]: choose compact or spacious\n' > "$status"
printf 'paused: awaiting captain response mentioning [key=grid]\n' >> "$status"
printf 'paused [key=grid]: still awaiting captain response\n' >> "$status"
printf '%s\n' '=== Before answer: wake drain still lists the key ==='
FM_STATE_OVERRIDE="$demo/home/state" "$repo/bin/fm-wake-drain.sh" 2>/dev/null
printf '%s\n' '=== Captain answers with fm-send --resolve-key ==='
set +e
PATH="$demo/fakebin:$PATH" FM_ROOT_OVERRIDE="$demo/home" FM_HOME="$demo/home" FM_SEND_SETTLE=0 \
  FM_CLASSIFY_RESOLVE_VERB=paused "$repo/bin/fm-send.sh" task --resolve-key grid 'use compact' 2>&1
rc=$?
set -e
printf 'fm-send exit code: %s\n' "$rc"
printf '%s\n' '=== Persisted decision ledger ==='
cat "$status"
printf '%s\n' '=== After explicit answer: wake drain output ==='
after=$(FM_STATE_OVERRIDE="$demo/home/state" "$repo/bin/fm-wake-drain.sh" 2>/dev/null)
if [ -n "$after" ]; then printf '%s\n' "$after"; else printf '%s\n' '(no open decisions)'; fi
exit "$rc"
