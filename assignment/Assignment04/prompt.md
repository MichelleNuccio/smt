# Tracing the sky

## Overview

I want to build an offline, browser-based sandbox called **Tracing the sky**.

The project explores how the sky above the same place has changed with the arrival and growth of the Starlink constellation. It transforms predicted satellite passes into an image: each satellite leaves a persistent trace, and multiple exposures can be accumulated as layers.

The result should feel like an artwork made from real orbital data. It should also make clear which dates the available data can support.

Use only Starlink constellation satellites. Exclude the early experimental prototypes, other satellite constellations, rocket bodies and debris.

Read and follow the course kit’s `AGENTS.md`. Ask me about unresolved decisions before building. Do not invent data or silently replace missing orbital records with current ones.

All interface text must be in English.

## Available data

The project currently has these files:

- `data/Original/starlink_gp.json`: current Starlink GP orbital elements downloaded from CelesTrak on October 7, 2026. This contains 11,110 records with different orbital epochs. It is a snapshot, not an archive of the entire year or month.
- `data/Original/satcat.tsv`: the satellite catalog I supplied. Use it for identifiers, names, launch dates and other relevant metadata.
- `data/tle2019.txt`: the historical 2019 Space-Track archive I downloaded and extracted. Preserve this file unchanged.
- `data/Processed/starlink_2019.tle`: an existing extraction containing 29,882 orbital element sets for 128 distinct Starlink satellites. Their catalog launch dates are May 24 and November 11, 2019.
- Notes about the available files are in `data/Original/SOURCES.md` and `data/Processed/starlink_2019_notes.md`.

Verify the files, identifiers and record counts before using them. Each historical TLE pair describes an orbit at an epoch; it is not an observed pass or a separate satellite.

The existing historical extraction is preliminary. Check its selection against the catalog and confirm that it excludes prototypes and non-satellite objects.

Sources:

- CelesTrak Starlink GP data: https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=json
- CelesTrak format documentation: https://celestrak.org/NORAD/documentation/gp-data-formats.php
- Space-Track archive documentation: https://www.space-track.org/documentation
- GCAT catalog and documentation: https://planet4589.org/space/gcat/

Confirm the provenance of my `satcat.tsv` before labeling it as a particular GCAT release.

## Objectives

The visitor should be able to:

1. Choose New York or Milan.
2. Choose a calendar date and an exposure start and end time.
3. Start the simulation and watch satellite traces accumulate.
4. Preserve the exposure as a layer.
5. Add further exposures to the same image, including exposures from different years.
6. Show or hide individual layers.
7. Toggle satellite names.
8. Export the visible composition as a PNG with the city and exposure intervals.

The historical reference begins in **2018**, the year before the first constellation launch in 2019. Because prototypes are excluded, 2018 represents the period before this constellation.

This version uses the data already available. It does not need to download missing years.

The calendar may allow dates from 2018 through the latest available dataset date, but unsupported dates must be clearly identified.

## Cities and time

Provide two offline city choices: **New York** and **Milan**.

Use documented coordinates for a representative point in each city. Cite their source and identify the point used. Do not request browser geolocation.

Use the appropriate city time zones:

- New York: `America/New_York`
- Milan: `Europe/Rome`

Display exposure times in the selected city’s local time and convert them correctly to UTC for orbital calculations. Handle daylight saving time and ambiguous or nonexistent local times explicitly.

The initial exposure duration should be **2 hours**. Allow durations from **1 minute to 6 hours**, including exposures crossing midnight. These limits are design assumptions, not scientific thresholds.

Ask me to choose the initial city, date and start time before implementing the initial view.

## Data preparation

Follow the preparation workflow in `AGENTS.md`.

Preserve all original data. Put derived files in `data/Processed`.

The preparation should:

1. Read the supplied catalog and orbital files.
2. Identify Starlink constellation satellites and exclude prototypes, debris and rocket bodies.
3. Match historical orbital records to catalog metadata using catalog identifiers.
4. Preserve the orbital epoch of every retained element set.
5. Report unmatched records, invalid records and exclusions.
6. Produce the compact data needed by the page.
7. Document the actual temporal coverage.

Do not treat all historical records as different satellites. Group them by satellite identifier while retaining the epochs needed to choose appropriate orbital elements.

Do not filter historical satellites using their present operational status: a satellite that has since reentered may still belong in a historical exposure.

Do not silently sample satellites or discard dates to meet the file size requirement. If reduction is necessary, explain the proposed reduction and ask me to decide.

## The rule

For each simulation instant:

1. Select an appropriate orbital element set for each satellite at that time.
2. Calculate the satellite position using a verified SGP4 implementation compatible with the supplied elements.
3. Transform the position into azimuth and elevation relative to the selected city.
4. Draw only the part of the trajectory above the observer’s geometric horizon.
5. Project the trajectory into the circular sky view.
6. Extend the satellite’s persistent trace within the current exposure layer.

Use these units:

- orbital distances: kilometres;
- observer altitude: metres;
- azimuth and elevation: degrees;
- exposure duration: seconds or minutes, labeled clearly;
- orbital epoch and calculations: UTC;
- displayed exposure times: the selected city’s local time.

Use a circular projection with:

- zenith at the centre;
- horizon at the circumference;
- north at the top;
- east on the right;
- south at the bottom;
- west on the left.

Use an azimuthal equidistant projection, with radial distance proportional to zenith angle. This is a representation choice, not a measured property of the sky.

The view remains fixed relative to the local horizon. It does not follow a star or satellite.

Include all eligible Starlink satellites whose predicted trajectories enter the visible sky. Do not filter by sunlight, apparent brightness or operational status.

These traces represent **predicted geometric passes**, not guaranteed visible photographic streaks.

Do not draw lines between different satellites. Do not invent branching paths or connection points to imitate the reference image.

Use temporal sampling fine enough to resolve trajectories and horizon crossings. Explain the chosen calculation step and verify its effect on the resulting paths. Keep calculation resolution separate from animation playback speed.

Break a trace when a satellite is below the horizon, when orbital data becomes unavailable or when calculation fails. Never join across such gaps.

## Orbital coverage and missing data

Do not propagate the October 2026 snapshot arbitrarily backward to reconstruct historical years.

For 2019, use historical elements near the selected exposure time. For 2026, use the snapshot only within a justified interval near each record’s epoch.

Before implementing, propose an orbital-age cutoff, explain its basis and ask me to approve it. It must be described as a modeling assumption unless supported by a source; it must not imply guaranteed positional accuracy.

Respect launch and reentry information where it is sufficiently documented. Explain how uncertain dates are handled.

Distinguish:

- **Before the first Starlink constellation launch:** no eligible constellation satellites.
- **Missing orbital data:** the available files do not support calculation for the selected time or satellite.
- **No passes during this exposure:** usable data was evaluated but produced no above-horizon trajectories.

Missing periods contribute no invented traces. Existing layers remain visible when a newly added exposure has missing data.

If only part of an exposure or satellite population has usable data, draw the supported portion and identify the omissions. Do not describe partial coverage as complete.

## The run and layers

The visitor chooses a date, start time and end time, then starts the exposure.

The simulation clock advances through that interval. Traces appear progressively and remain in the image.

Provide play, pause and a way to scrub through the current exposure. Scrubbing backward must show only the traces accumulated up to that instant; it must not retain paths from the future.

Simulation speed changes playback only. It must not change the calculated trajectories or exposure duration.

Each exposure becomes a separate layer. Starting another exposure adds it to the composition.

Each layer should retain:

- city;
- start and end timestamps;
- time zone;
- colour;
- visibility;
- orbital coverage information needed by the missing-data panel.

Give comparison layers distinct colours, beginning with violet. Colours distinguish exposures; they do not encode brightness or physical satellite properties.

Allow individual layers to be shown or hidden.

Prevent layers from different cities from being silently combined. Ask me how switching cities should affect an existing composition before implementing that behaviour.

Do not add layer deletion, opacity sliders or other controls without discussing them with me.

## Visual design

Use a black background and **Roboto** for all text.

Embed the font so the page and exported image work offline. Do not load Google Fonts or another font service at runtime.

The attached visual reference guides the aesthetic:

- very thin violet lines;
- low-opacity traces;
- delicate luminous appearance;
- overlapping paths that become visually denser;
- restrained labels.

The reference is inspiration for style, not a diagram to reproduce. The paths must come from the orbital calculation.

Keep the circular sky image visually dominant. Do not add stars, map tiles, a globe, terrain or a decorative network.

Provide a switch labeled **“Show satellite names”**. Names should identify the actual satellites. Propose a legible placement method and ask me before choosing which labels to suppress if they overlap.

The title is **“Tracing the sky”**.

Include a short description explaining that this is an artistic accumulation of predicted Starlink passes above a selected city, allowing exposures from different dates to be compared.

## Interface

Follow the ordering in `AGENTS.md`:

1. Clock, date and exposure interval.
2. How the image is drawn, including the name toggle and layer visibility.
3. Main choices, including city.
4. Finer assumptions, if agreed with me.

Include:

- the title and short description;
- the central circular sky;
- city selection;
- date and exposure interval selection;
- simulation playback;
- exposure layers;
- satellite-name switch;
- PNG export;
- limitations and citations;
- a side panel dedicated to missing orbital data.

The missing-data panel should identify the affected exposure, period and satellites when known. If an entire period lacks an archive, say that directly; do not fabricate a list of absent satellites.

Do not add coverage maps, connection estimates, service capacity, collision predictions or unrelated statistics.

## PNG export

Export the visible composition as a PNG on a black background.

Include:

- the sky circle and visible traces;
- satellite names if the name switch is enabled;
- the city;
- each visible exposure’s start and end time;
- time-zone information;
- a compact colour key for multiple exposures;
- a brief missing-data indication when a visible exposure has incomplete coverage.

Exclude interactive controls and the full side panel from the artwork.

Wait for the embedded Roboto font to load before exporting.

Ask me to choose the export dimensions before implementing them.

## Limitations and citations

Explain on the page that:

- the trajectories are predictions from orbital elements;
- orbital data is unevenly available across dates and satellites;
- the current snapshot does not cover all of 2026;
- missing traces do not prove that the sky was empty;
- brightness, sunlight, clouds, buildings and camera sensitivity are not modeled;
- trace colour, thickness and glow are artistic choices;
- a chosen exposure is not an annual average;
- the view represents a fixed local horizon.

Provide citations for every dataset and library used. Label unsupported numeric choices as assumptions.

## Deliverable and validation

Produce one self-contained `index.html`, under 50 MB, with styles, scripts, libraries, font and data inline.

It must open from disk with Wi-Fi off and make no network requests.

Also preserve the preparation script and derived data as required by `AGENTS.md`.

Verify:

- historical dates use historical elements;
- missing dates do not reuse current orbits;
- the 2018 reference excludes prototypes;
- city time zones and midnight crossings work;
- paths do not connect across the horizon or data gaps;
- pausing and scrubbing preserve the correct exposure state;
- adding an exposure retains previous layers;
- hiding a layer also hides it in the export;
- the name switch affects the exported PNG;
- the exported city and intervals match the visible layers;
- the page works offline and satisfies the file size limit.

Before building, summarize the proposed implementation and ask me the remaining questions. This is the course’s single implementation run: preserve and report what comes out, including limitations and failures.