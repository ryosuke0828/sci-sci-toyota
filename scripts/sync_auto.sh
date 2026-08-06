#!/bin/zsh
# Drive外の自動取得ディレクトリ(~/scisci-auto)とリポジトリを双方向に同期する。
#
# なぜ必要か:
#   macOS のプライバシー保護(TCC)により、launchd が起動したプロセスは
#   Google Drive 配下を読めない。そのため自動取得は ~/scisci-auto で行い、
#   結果はこのスクリプトでリポジトリに持ってくる。
#   このスクリプトは Claude Code（TCC 許可あり）から実行する前提。
#
# 使い方:
#   scripts/sync_auto.sh          … 双方向（push してから pull）
#   scripts/sync_auto.sh push     … リポジトリ → ~/scisci-auto（入力とスクリプトを更新）
#   scripts/sync_auto.sh pull     … ~/scisci-auto → リポジトリ（取得結果を回収）

set -u

REPO="/Users/jinedinujidan/Library/CloudStorage/GoogleDrive-r.ikura@msp-lab.org/My Drive/others/TA:RA/Sci-sci"
AUTO="$HOME/scisci-auto"
MODE="${1:-both}"

if [[ ! -d "$AUTO" ]]; then
  echo "!! $AUTO がありません。自動取得の設定がまだです。"
  exit 1
fi

do_push() {
  echo "--- push: リポジトリ → ~/scisci-auto ---"
  # 取得スクリプトを更新（リポジトリ側が正）。
  # これを忘れると自動実行が古いコードのまま走り続けるので必ず流すこと。
  cp "$REPO/src/openalex_link_toyota_papers.py" "$AUTO/src/" && echo "  取得スクリプトを更新"
  cp "$REPO/data/derived/toyota_official_scrape/combined_papers.csv" \
     "$AUTO/input/" && echo "  入力CSVを更新（$(wc -l < "$AUTO/input/combined_papers.csv") 行）"
}

do_pull() {
  echo "--- pull: ~/scisci-auto → リポジトリ ---"
  if [[ -z "$(ls -A "$AUTO/out" 2>/dev/null)" ]]; then
    echo "  取得結果がまだありません（自動実行が未完了）。"
  else
    mkdir -p "$REPO/data/derived/openalex_linking"
    cp "$AUTO"/out/* "$REPO/data/derived/openalex_linking/" && \
      echo "  取得結果を回収: $(ls "$AUTO/out" | tr '\n' ' ')"
  fi
  if [[ -f "$AUTO/cache/openalex_linking_cache.json" ]]; then
    mkdir -p "$REPO/data/cache"
    cp "$AUTO/cache/openalex_linking_cache.json" "$REPO/data/cache/" && \
      echo "  キャッシュを回収"
  fi
  echo ""
  echo "--- 自動取得の進捗（~/scisci-auto/FETCH_DIGEST.md）---"
  if [[ -f "$AUTO/FETCH_DIGEST.md" ]]; then
    tail -20 "$AUTO/FETCH_DIGEST.md"
  else
    echo "  まだ記録がありません。"
  fi
}

case "$MODE" in
  push) do_push ;;
  pull) do_pull ;;
  both) do_push; echo ""; do_pull ;;
  *) echo "使い方: $0 [push|pull|both]"; exit 1 ;;
esac
