#!/usr/bin/env bash
set -euo pipefail

ROMS_ROOT="/storage/7FBF-F7F4/roms"
DST_ROOT="/sdcard/ES-DE/gamelists"

echo "Listing systems under $ROMS_ROOT ..."

systems=$(adb shell "for d in '$ROMS_ROOT'/*; do [ -d \"\$d\" ] && basename \"\$d\"; done" | tr -d '\r')

if [ -z "$systems" ]; then
  echo "No subfolders found under $ROMS_ROOT"
  exit 0
fi

for system in $systems; do
  src="$ROMS_ROOT/$system/gamelist.xml"
  dst_dir="$DST_ROOT/$system"
  dst="$dst_dir/gamelist.xml"
  bk="$dst_dir/gamelist.xml_bk"

  echo "==== [$system] ===="

  # 1) src xml nonexist -> skip
  if ! adb shell "[ -f '$src' ]"; then
    echo "skip: source not found: $src"
    continue
  fi

  # 2) create dst folder if needed
  adb shell "mkdir -p '$dst_dir'"

  # 3) if dst exists, rename to gamelist.xml_bk
  if adb shell "[ -e '$dst' ]"; then
    echo "backup existing dst -> $bk"
    adb shell "rm -f '$bk'; mv '$dst' '$bk'"
  fi

  # 4) copy src -> dst
  echo "copy: $src -> $dst"
  adb shell "cp '$src' '$dst'"

done

echo "Done."