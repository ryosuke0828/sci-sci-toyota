#!/bin/zsh
# リポジトリを Google Drive の外へミラーする。
#
# なぜ必要か:
#   2026-08-06、Google Drive.app の更新(v128→v129)と再起動をきっかけに、
#   リポジトリのフォルダが 2026-07-27 の状態へ巻き戻り、
#   8/3 に作成した成果物（スクリプト・レポート・派生データ）を失った。
#   Drive の中で git init しても、Drive ごと巻き戻れば .git も一緒に消えるため
#   対策にならない。**Drive の外に実体のコピーを置くこと**が対策になる。
#   （恒久対策は GitHub リモートへの push。それまでのつなぎ。）
#
# 使い方:
#   scripts/backup_repo.sh          … ~/scisci-backup/current へミラー
#   scripts/backup_repo.sh snapshot … 日付つきスナップショットも残す
#
# Claude Code から実行する前提（launchd は Drive を読めないため）。

set -u

REPO="/Users/jinedinujidan/Library/CloudStorage/GoogleDrive-r.ikura@msp-lab.org/My Drive/others/TA:RA/Sci-sci"
DEST="$HOME/scisci-backup"
MODE="${1:-mirror}"

mkdir -p "$DEST/current"

# 巨大なキャッシュ（最大150MB）は除外する。失っても再取得できるうえ、
# OpenAlex 紐付けキャッシュだけは ~/scisci-auto 側に実体がある。
EXCLUDES=(
  --exclude "data/cache/openalex_random_impact_rule.json"
  --exclude "data/cache/openalex_h_index_prediction.json"
  --exclude ".DS_Store"
)

echo "--- ミラー: リポジトリ → ~/scisci-backup/current ---"
rsync -a --delete "${EXCLUDES[@]}" "$REPO/" "$DEST/current/"
echo "  $(find "$DEST/current" -type f | wc -l | tr -d ' ') ファイル / $(du -sh "$DEST/current" | cut -f1)"

if [[ "$MODE" == "snapshot" ]]; then
  STAMP=$(date "+%Y-%m-%d_%H%M")
  echo "--- スナップショット: $STAMP ---"
  # ハードリンクで容量を節約しつつ、その時点の状態を固定する
  cp -al "$DEST/current" "$DEST/snapshot_$STAMP" 2>/dev/null || \
    cp -a "$DEST/current" "$DEST/snapshot_$STAMP"
  echo "  $DEST/snapshot_$STAMP"
  # スナップショットは直近10世代だけ残す。
  # macOS(BSD)の head は `head -n -10`（末尾から数える指定）を受け付けないので、
  # 新しい順に並べて11件目以降を消す。
  ls -1d "$DEST"/snapshot_* 2>/dev/null | sort -r | tail -n +11 | while read -r old; do
    rm -rf "$old" && echo "  古いスナップショットを削除: $(basename "$old")"
  done
fi

echo "完了: $(date '+%Y-%m-%d %H:%M:%S')"
