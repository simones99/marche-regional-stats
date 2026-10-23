# Showcase

This folder holds the showcase page, `index.html` and `style.css`. `marche-stats build-showcase` assembles it with the report exports into `build/showcase/`; this README stays out of the build.

The rest of this file is the recording script for the four clips of the report's interactions, which will sit next to the pages they belong to. With it, all four can be recorded in one Power BI Desktop session and any of them redone later. It ends with the commands that turn a recording into a clip and its poster.

The clips will be muted MP4 files (H.264, 1280 px wide, under 2 MB each), tracked in git without LFS. The page will play them muted, in a loop and inline. With reduced motion it will show the poster and the controls instead.

## File names

Paths are relative to this folder. The page will reference exactly these names, so the showcase test will fail if one of the files is missing.

| Clip | Video | Poster |
|---|---|---|
| (a) Benchmark: `Compare to` | `clips/benchmark-compare.mp4` | `clips/benchmark-compare.jpg` |
| (b) Provinces: indicator selector | `clips/provinces-indicator.mp4` | `clips/provinces-indicator.jpg` |
| (c) Provinces to Province detail: drill-through | `clips/provinces-drillthrough.mp4` | `clips/provinces-drillthrough.jpg` |
| (d) Business deep dive: forecast tooltip | `clips/business-forecast.mp4` | `clips/business-forecast.jpg` |

To redo a clip, overwrite both files with the same names.

## Before recording

1. Open `powerbi/marche-regional-profile.pbip` in Power BI Desktop and refresh, so the data matches the exports in `powerbi/exports/`.
2. Set Desktop to English (File > Options and settings > Options > Global > Regional settings, application language English) and restart it. The right-click menu in clip (c) and the tooltip in clip (d) follow the Desktop language.
3. Maximize the Desktop window, close the Filters pane and collapse the Visualizations and Data panes, so the report canvas is as wide as possible.
4. View > Page view > Fit to page.
5. Check the starting state of each page below. Slicer selections are saved with the report, so a page left in another state opens in that state.
6. Keep the pointer off the canvas between actions. Hovering a visual shows its header icons, which add noise to the clip.

In Desktop a slicer reacts to a plain click, while buttons (the Back button, the page navigator) need Ctrl+click. Move the pointer slowly and pause about two seconds after each change, so a viewer can read the result.

## Recording script

### (a) Benchmark: `Compare to` from Italy to the EU to the neighbouring regions

- **Page:** Benchmark.
- **Starting state:** `Value` selected in the four buttons at the top right (`Value`, `vs Country`, `vs EU`, `vs Neighbours avg`). The *Indicators by Area* matrix shows Marche, the five neighbouring regions (Abruzzo, Emilia-Romagna, Lazio, Toscana, Umbria), Italy and EU-27 for six indicators.
- **Actions:**
  1. Hold on the starting state for 2 seconds.
  2. Click `vs Country`: every cell of the matrix becomes the difference from Italy. Hold 2–3 seconds.
  3. Click `vs EU`: the differences are now from the EU-27. Hold 2–3 seconds.
  4. Click `vs Neighbours avg`: the differences are from the average of the neighbouring regions. Hold 2–3 seconds.
  5. Click `Value` to return to the starting state, so the loop joins up.
- **What changes:** only the *Indicators by Area* matrix. The dot plot, the headline and the *Rank among Neighbours* table do not react to the buttons, so keep the matrix in the middle of the viewer's attention by moving the pointer only between the buttons.
- **Length:** about 12 seconds.
- **Poster:** the frame after `vs EU`, with the matrix showing the differences from the EU.

### (b) Provinces: the indicator selector recolouring the map

- **Page:** Provinces.
- **Starting state:** `Population change 5y %` selected in the *Province indicator* slicer. The headline reads "Population fell least in Ancona" and the map is shaded by population change.
- **Actions:**
  1. Hold on the starting state for 2 seconds.
  2. Click `Share aged 65+`. The map is recoloured and its legend and labels change. The headline names the province with the highest value, and the matching column of *All Indicators by Province* is shaded. Hold 2 seconds.
  3. Click `Companies per 1,000 residents`. Hold 2 seconds.
  4. Click `GDP per inhabitant (EUR)`. Hold 2 seconds.
  5. Click `Population change 5y %` to return to the starting state.
- `Crude death rate per 1,000` is the fifth option; it is left out to keep the clip short, and can replace any of the three middle steps.
- **Length:** about 12 seconds.
- **Poster:** the frame after `Companies per 1,000 residents`, with the map recoloured.

### (c) Provinces to Province detail: the drill-through

- **Page:** Provinces, then the hidden Province detail page.
- **Starting state:** as at the end of clip (b), `Population change 5y %` selected. The note at the bottom right of the page reads "Right-click a province › Drill through › Province detail".
- **Actions:**
  1. Hold on the starting state for 2 seconds.
  2. In the *All Indicators by Province* table, right-click the `Macerata` row. The map is an image drawn by a DAX measure and cannot start a drill-through; the table can.
  3. In the menu, point to `Drill through` and click `Province detail`.
  4. Province detail opens for Macerata: headline, the five indicator cards with the gap to the region, the line of active companies since December 2009 and the change by sector. Hold 3–4 seconds.
  5. Ctrl+click the `Back` button at the top of the page to return to Provinces.
- Province detail was last saved drilled to Ascoli Piceno; drilling to Macerata shows that the page follows the province clicked. Any province other than the one on the page works.
- **Length:** about 12 seconds.
- **Poster:** the Province detail page for Macerata.

### (d) Business deep dive: the tooltip on the SARIMA forecast and its interval

- **Page:** Business deep dive.
- **Starting state:** the page as saved. The chart at the top right, *Active Companies: Last 24 Months and 12-Month SARIMA Forecast*, shows the last 24 months as a solid line, the forecast from February 2025 to January 2026 as a dashed line with hollow markers, and the 95 % interval as a grey band.
- **Actions:**
  1. Hold on the starting state for 2 seconds.
  2. Hover the last solid point (January 2025): the tooltip shows the actual count. Hold 2 seconds.
  3. Move right along the dashed line, pausing on two or three months (for example June 2025 and October 2025): the tooltip shows the month, the forecast and its lower and upper 95 % bounds.
  4. Stop on January 2026, where the interval is widest (about 124,700 to 131,000 against a forecast of about 127,800). Hold 3 seconds.
  5. Move the pointer off the chart so the tooltip closes and the loop joins up.
- The tooltip is the default one: next to `Forecast chart actual` and `Forecast chart forecast`, the error bars of the forecast add its 95 % bounds as `Upper` and `Lower`.
- **Length:** about 12 seconds.
- **Poster:** the frame with the tooltip open on January 2026.

## Recording with the Xbox Game Bar

The Xbox Game Bar is built into Windows and records one app window, not the whole screen, so it records only the Power BI Desktop window.

1. In Settings > Gaming > Captures, turn off audio capture, turn on *Capture mouse cursor when recording a game* (the cursor shows what is clicked), and set the video frame rate to 30 fps.
2. Click inside the Power BI Desktop window so it has the focus.
3. Press Win+Alt+R to start recording. A small timer appears; it is not part of the recording.
4. Perform the actions for one clip, then press Win+Alt+R again to stop.
5. Repeat for the next clip. One recording per clip keeps the trimming simple.

Recordings land in `%USERPROFILE%\Videos\Captures` (the folder is shown, and can be changed, in Settings > Gaming > Captures), named after the window and the time, for example `Power BI Desktop 2026-10-22 15-04-11.mp4`. They are large and full of the window's ribbon and panes; the commands below trim, crop, scale and compress them. Keep the raw recordings out of the repository.

## Compressing a clip

The commands use [ffmpeg](https://ffmpeg.org/). If it is not installed, install it with `winget install Gyan.FFmpeg`, then open a new terminal so `ffmpeg` is on the path.

Run them from this folder (`showcase/`). The examples are for clip (a). For the others, change the recording in `$rec` and the output names:

```powershell
$rec = "$env:USERPROFILE\Videos\Captures\Power BI Desktop 2026-10-22 15-04-11.mp4"
```

**1. Find the trim points and the canvas.** Play the recording and note the second where the clip should start and end. To crop away the Desktop ribbon and panes, save one frame and read the report canvas's top-left corner, width and height in Paint (the pixel position is shown in the status bar):

```powershell
ffmpeg -ss 1 -i $rec -frames:v 1 frame.png
```

Delete `frame.png` afterwards.

**2. Compress.** H.264, 1280 px wide, no audio track, `yuv420p` so every browser can play it, and `+faststart` so playback starts before the file has finished downloading:

```powershell
ffmpeg -i $rec -ss 1.5 -to 13.5 -an -vf "crop=W:H:X:Y,scale=1280:-2:flags=lanczos,fps=30" -c:v libx264 -preset slow -crf 26 -profile:v high -pix_fmt yuv420p -movflags +faststart clips/benchmark-compare.mp4
```

- `-ss` and `-to` are the start and end seconds in the recording.
- `crop=W:H:X:Y` is the canvas width, height and top-left corner from step 1, for example `crop=1504:846:208:150`. Leave the crop out (`-vf "scale=1280:-2:flags=lanczos,fps=30"`) to keep the whole Desktop window. If the cropped canvas is narrower than 1280 px, the clip is scaled up and looks softer; collapse more panes and record again.
- `scale=1280:-2` sets the width to 1280 px and keeps the aspect ratio with an even height, which H.264 requires.
- `-an` drops the audio track, so the clip is muted whatever the recording settings were.

**3. Check the size.** It must be under 2 MB:

```powershell
(Get-Item clips/benchmark-compare.mp4).Length / 1MB
```

If it is larger, raise `-crf` by 2 (28, then 30) and run step 2 again, or lower `fps=30` to `fps=24`. A shorter clip is the other lever: trim the holds before lowering the quality further.

## Taking the poster

Take the poster from the compressed clip, so it has the same size and crop. `-ss` is the second of the frame named in the clip's script:

```powershell
ffmpeg -ss 7 -i clips/benchmark-compare.mp4 -frames:v 1 -q:v 3 clips/benchmark-compare.jpg
```

`-q:v` sets the JPEG quality (2 is best, 31 worst); 3 keeps the poster sharp at a fraction of a PNG's size. The poster is shown before the clip starts and, with reduced motion, until the viewer presses play.
