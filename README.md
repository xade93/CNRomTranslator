Out of frustration I vibe-coded this short script. Its basically a wrapper for https://github.com/yingw/rom-name-cn CSV files
 
what it does is it takes output of Chinese ROM names from e.g.

```bash
printf "%s\n" *.iso *.cso 2>/dev/null  # e.g. for PSP ROMs
```
and for each filename it attempts to fuzzily match CN name to canonical English name via (e.g.) `rom_name_cn/Sony - PlayStation Portable.csv`, and for each confidence below threshol (e.g. 80) it interactively ask for manual intervention. Eventually it generates a gamelist.xml compatible with e.g. ES-DE which can be imported to handhelds and scrapers can take it from there.

The benefit of this method is 
1. If you already have large amount of ROMs on sdcard, this wont involve costy file move, delete, upload to PC etc. Even your original filename is preserved as it may hint information about translators. Only single XML is changed for each system. For the same reason if you have some image assets assets beforehand this wont lose it.
2. Its incredibly easy to mass perform, even when you dont have a SD card. `adb shell` into the device, preview generated XML, backup & replace XML, start scraper.
3. Before you confirm the XML the operation is non-destructive. Even after replacing XML your original image assets are preserved and are *likely* still displayed (unless you have nonstandard image names / extra text metadata / rating etc, in that case we need to merge old XML with new one, which is a feature I dont need)

I believe you will likely find this helpful if you are reading this.

You can use it this way:

```bash
# install requirements manually
% python rom_fuzzy_translate.py "Sony - PlayStation Portable" --csv-dir ./rom-name-cn --th 80
```
