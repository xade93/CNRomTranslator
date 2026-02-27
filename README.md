Can use it this way:

```
  % python rom_fuzzy_translate.py "Sony -
  PlayStation Portable" --csv-dir ./rom-name-
  cn --th 80
```
 
  what it does is it takes output of game
  ROMS from e.g.

``` 
  printf "%s\n" *.iso *.cso 2>/dev/null
```

  and for each filename attempt to fuzzily match CN name to canonical English name via the "rom_name_cn/Sony -
    PlayStation Portable.csv", and for each
  confidence below threshol (e.g. 80) it
  interactively ask for manual intervention.
  Eventually it generates a gamelist.xml
  compatible with e.g. ES-DE which can be
  imported to handhelds and scrapers can take
  it from there.

