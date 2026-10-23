# Routes: Planning and Import

Everything about where routes come from, their format, and their coordinate systems.

## Route file format

A route is a plain text file with one coordinate per line:

```
121.43680706489432,31.027665038002322
121.43692833613818,31.027541257648274
121.43703613279938,31.02741360898802
```

- Each line is `longitude,latitude` — **longitude first**, comma-separated.
- Encoded in **BD09** (Baidu), **not** raw GPS WGS84.
- The line order is the travel order. The closer the first and last points, the better the result.

## Coordinate systems

This is where people get burned:

| System | Used for |
| --- | --- |
| **WGS84** | Raw GPS; OpenStreetMap tiles are WGS84 |
| **GCJ02** | Amap / Tencent maps; **the client shifts to this before uploading** |
| **BD09** | Baidu maps; **this is what route files store** |

The desktop **route preview map uses OpenStreetMap only**; the **route planner defaults to Baidu Maps** and can switch to OpenStreetMap in the page. Baidu clicks are already BD09; OSM clicks are WGS84 and are converted to BD09 before being stored, so exported txt files remain compatible with legacy routes and with the upload pipeline. Mobile keeps using BD09.

> The **desktop route planner** defaults to Baidu Maps and can switch to Leaflet + OpenStreetMap; the route preview uses OpenStreetMap only. **Android / HarmonyOS** route design still uses the Baidu Maps API. Only the base map differs — the exported coordinate format is identical.

## Route planner (desktop)

1. Click "Design route" on the Routes page to open the embedded planner over loopback HTTP. Keep the client running to reload it, and reopen from the app after restarting the client.
2. Click points on the map to trace a route (Baidu Maps by default, switchable to OpenStreetMap in the page).
3. You can **add, remove individual points, or clear all points**.
4. Click "Download route txt" to get `custom_route.txt`.
5. Back on the Routes page, click **Import TXT** to import it.

The route is copied into the **`routes/` folder in the OS user data directory** (see [desktop.md](desktop.md)) and survives restarts.

## Built-in routes and the quarantine folder

- Only `assets/Routes/default.txt` ships as a built-in route today.
- The remaining historical routes moved to `assets/Routes/NeedsReview/` (`BigLawn`, `BotanicalGarden`, `HanzeLake`, `NanTi`, `SiyuanLake`) pending manual verification of jump segments, length and endpoints.
- Routes you import yourself are copied into the user data directory’s `routes/` folder.

> ⚠️ `assets/Routes/NeedsReview/` is a quarantine area. **Do not** move entries back into the built-in list directly — several have jump or length defects that must be validated first.

## Verifying a route

1. Select it in the desktop "Select route" dropdown.
2. The Workbench and Routes pages automatically preview the current per-run distance without login and update when you select another route. The map opens by default; if collapsed, click "Open in map".
3. Check the OpenStreetMap embedded in the preview card:
   - Any red highlighted segment means a jump (> 150 m);
   - Whether the green start and red finish are close together;
   - Whether total length matches your target distance.

A route with no red segments and close endpoints is a valid built-in candidate.

## Route design (Android / HarmonyOS)

1. Open the route design page and tap points **in order**.
2. More points fit better. **Order matters, and start/finish should be close.**

![Android route design](../images/android-route.webp)

## Deleting an imported route

The "Delete" button on the Routes page removes a copy from the user data directory’s `routes/` after confirmation; the imported source remains untouched.

- The desktop built-in route is displayed as “思源湖” (Siyuan Lake; internal identifier: `default`) and is **protected**. Legacy `user.txt` must be imported manually.
- Importing a duplicate name appends `_1`, `_2`, etc. instead of overwriting.
