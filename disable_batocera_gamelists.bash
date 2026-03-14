#!/usr/bin/env bash
set -euo pipefail

ROMS_ROOT="/storage/7FBF-F7F4/roms"

echo "Renaming source gamelist.xml -> gamelist.xml_bk under $ROMS_ROOT ..."

systems=$(adb shell "for d in '$ROMS_ROOT'/*; do [ -d \"\$d\" ] && basename \"\$d\"; done" | tr -d '\r')

if [ -z "$systems" ]; then
  echo "No subfolders found under $ROMS_ROOT"
  exit 0
fi

for system in $systems; do
  src_dir="$ROMS_ROOT/$system"
  src="$src_dir/gamelist.xml"
  bk="$src_dir/gamelist.xml_bk"

  echo "==== [$system] ===="

  if ! adb shell "[ -f '$src' ]"; then
    echo "skip: source not found: $src"
    continue
  fi

  if adb shell "[ -e '$bk' ]"; then
    echo "remove old backup: $bk"
    adb shell "rm -f '$bk'"
  fi

  echo "rename: $src -> $bk"
  adb shell "mv '$src' '$bk'"
done

echo "Done."