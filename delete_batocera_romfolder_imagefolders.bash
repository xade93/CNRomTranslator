#!/usr/bin/env bash
set -euo pipefail

ROMS_ROOT="/storage/7FBF-F7F4/roms"

echo "Scanning for source images/ folders under $ROMS_ROOT ..."
echo

systems=$(adb shell "for d in '$ROMS_ROOT'/*; do [ -d \"\$d\" ] && basename \"\$d\"; done" | tr -d '\r')

if [ -z "${systems:-}" ]; then
  echo "No subfolders found under $ROMS_ROOT"
  exit 0
fi

for system in $systems; do
  img_dir="$ROMS_ROOT/$system/images"

  if ! adb shell "[ -d '$img_dir' ]"; then
    continue
  fi

  # Count entries recursively. If find/wc acts weird, fall back to unknown.
  count=$(
    adb shell "find '$img_dir' -mindepth 1 | wc -l" 2>/dev/null \
      | tr -d '\r[:space:]' \
      || true
  )

  if [ -z "${count:-}" ]; then
    count="unknown"
  fi

  echo "Found: $img_dir"
  echo "Content count: $count"
  read -r -p "Delete this folder? [y/N/q] " ans

  case "$ans" in
    y|Y|yes|YES)
      echo "Deleting: $img_dir"
      adb shell "rm -rf '$img_dir'"
      echo "Deleted."
      ;;
    q|Q)
      echo "Quit."
      exit 0
      ;;
    *)
      echo "Skipped."
      ;;
  esac

  echo
done

echo "Done."