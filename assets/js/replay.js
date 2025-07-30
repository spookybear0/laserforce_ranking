

function isSoundLoaded(audio) {
    return audio["data"] != undefined;
}

function getAudioDurationSeconds(audio) {
    return audio["buffer"].duration;
}

async function playAudio(audio, stereo_balance) {
    // If this is the very first time we're playing a sound, create
    // the context. This must be done after the user clicked somewhere.
    if (audioContext == undefined) {
        audioContext = new AudioContext();
    }

    if (!isSoundLoaded(audio)) {
        // We haven't started loading this sound yet.
        return audio;
    }

    // If we loaded the sound but haven't decoded it yet, do that now.
    // TODO: This can cause race conditions if the same sound is played twice.
    if (audio["buffer"] == undefined) {
        audio["buffer"] = await audioContext.decodeAudioData(audio["data"]);
    }

    if (!recalculating) {
        const source = audioContext.createBufferSource();
        source.buffer = audio["buffer"];

        stereoPanner = audioContext.createStereoPanner();
        stereoPanner.pan.value = stereo_balance;

        const gainNode = audioContext.createGain();
        gainNode.gain.value = 0.5;

        source.connect(gainNode);
        gainNode.connect(stereoPanner);
        stereoPanner.connect(audioContext.destination);

        source.start();
        audio["source"] = source;
    }

    return audio;
}

function stopAudio(audio) {
    if (audio["source"] != undefined) {
        audio["source"].stop();
        audio["source"] = undefined;
    }
}

// We are not allowed to create an AudioContext until there is a user
// interaction.
audioContext = undefined;

// Keep the loading screen up until all these sounds have been loaded.
missing_sounds = [];

// Is everything we need loaded?
assets_loaded = false;

current_starting_sound_playing = undefined;

started = false;

// Index of the columns to sort by, in order of significance.
sort_columns = [];

// All team <table> elements.
team_tables = [];

// This value increases with every restart or start skip so we know
// whether or not the current start sound is relevant.
playback_key = 1

cancelled_starting_sound = false;
restarted = false; // True if the playback had been restarted
play = false; // Playback is currently in progress
scrub = false; // for when going back in time
recalculating = false; // for when we're mass recalculating and don't want to play audio
playback_speed = 1.0;
intro_sound = undefined;
start_sound = undefined;

columns = [];
team_names = [];
team_ids = [];

// The timestamp (wall clock) when we last started to play back or change the playback settings.
base_timestamp = 0;

// The game time in milliseconds at the time of base_timestamp.
base_game_time_millis = 0;

// The current time being shown in the time label, in seconds.
time_label_seconds = 0;

// The current real world timestamp being shown in the timestamp label, as a UNIX timestamp in seconds.
current_real_world_timestamp_seconds = 0;

// Sound IDs and all Audio objects for them.
sounds = {};

// Formatter for the real world timestamp. Basically MM/DD/YY HH:MM:SS (AM|PM)
// Note that we already receive the timestamp with the timezone baked in, so we need to explicitly
// set it to UTC so it doesn't get converted twice.
const real_world_timestamp_formatter = new Intl.DateTimeFormat('en-US', {
    year: '2-digit',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
    timeZone: 'UTC'
});

/* Returns the time in the game (in milliseconds) that's currently active. */
function getCurrentGameTimeMillis() {
    // If we're not currently playing back, the game time remains unchanged.
    if (!play) {
        return base_game_time_millis;
    }

    const now = new Date().getTime();

    return base_game_time_millis + (now - base_timestamp) * get_playback_speed();
}

function setSortColumns(new_sort_columns) {
    sort_columns = new_sort_columns;
}

// Compares two lists of values, in order of significance. 0 if they're both identical.
function compareValueList(a, b) {
    for (let i = 0; i < a.length; i++) {
        if (a[i] > b[i]) {
            return -1;
        }

        if (a[i] < b[i]) {
            return 1;
        }
    }

    return 0;
}

function sortTable(table) {
    if (sort_columns.length == 0) {
        return;
    }

    let rows = Array.from(table.querySelectorAll("tr"));

    rows = rows.slice(1);

    rows.sort( (r1,r2) => {
        let row_id1 = r1.id;
        let row_id2 = r2.id;
        let values1 = [];
        let values2 = [];

        sort_columns.forEach((column) => {
            values1.push(parseInt(document.getElementById(`${row_id1}_${column}`).innerHTML));
            values2.push(parseInt(document.getElementById(`${row_id2}_${column}`).innerHTML));
        });

        return compareValueList(values1, values2);
    });

    rows.forEach(row => table.appendChild(row));
}

function sortTables() {
    team_tables.forEach((table) => sortTable(table));
}

function beginPlayback() {
    play = true;
    restarted = false;
    playButton.innerHTML = "Pause";
    started = true;
    base_timestamp = new Date().getTime();
    current_starting_sound_playing = undefined;

    // play the game start sfx
    if (start_sound != undefined) {
        playSound(start_sound, 0.0);
    }

    playEvents();
}

async function playPause() {
    if (play) { // pause the game
        // Lock the game time at what it currently is.
        base_game_time_millis = getCurrentGameTimeMillis();
        base_timestamp = new Date().getTime();

        play = false;
        playButton.innerHTML = "Play";
    } else { // play the game
        base_timestamp = new Date().getTime();

        restarted = false;
        if (current_starting_sound_playing != undefined) {
            playback_key++; // cancel the callback for the starting sound
            // Cancel the intro sound.
            stopAudio(current_starting_sound_playing);
            current_starting_sound_playing = undefined;

            resetGame();
            beginPlayback();
        }
        else if (!started) {
            base_game_time_millis = 0
            // starting the game for the first time

            if (intro_sound != undefined) {
                audio = await playSound(intro_sound, 0.0);
                current_starting_sound_playing = audio;
                playback_key++;

                // wait for the sfx to finish
                setTimeout(function(key) {
                    // The intro sound is over, start the actual playback - but only
                    // if nothing has happened in the meantime (restart or pause).
                    if (key == playback_key) {
                        beginPlayback();
                    }
                }, getAudioDurationSeconds(audio)*1000, playback_key);
            } else {
                // No intro sound, start playing right away.
                beginPlayback();
            }
            return;
        }

        play = true;
        playButton.innerHTML = "Pause";
        restarted = false;
        playEvents();
    }
}

function addColumn(column_name) {
    columns.push(column_name);
}

function addTeam(team_name, team_id, team_css_class) {

    let team_div = document.createElement("div");
    team_div.id = team_id;
    team_div.className = "team";

    let team_score = document.createElement("h2");
    team_score.style = "font-size: 20px;";
    team_score.className = `team_score ${team_css_class}`;
    team_score.id = `${team_id}_score`;
    team_score.innerHTML = `${team_name}: 0`;
    team_div.appendChild(team_score);

    team_names.push(team_name);
    team_ids.push(team_id);

    let team_table = document.createElement("table");
    team_table.id = `${team_id}_table`;

    let header_row = document.createElement("tr");

    columns.forEach((column) => {
        let header = document.createElement("th");
        header.innerHTML += `<th><p>${column}</p></th>`;
        header_row.appendChild(header);
    });

    team_table.appendChild(header_row);
    team_div.appendChild(team_table);
    teams.appendChild(team_div);

    team_tables.push(team_table);
}

function registerSound(sound_id, asset_urls, priority, required) {
    sound_objects = [];

    asset_urls.forEach((asset_url) => {
        sound_objects.push({
            "asset_url": asset_url});
    });

    sounds[sound_id] = sound_objects;

    if (required) {
        missing_sounds.push(sound_id);
    }
}

async function loadAudioBuffer(audio) {
  const response = await fetch(audio["asset_url"]);
  if (!response.ok) {
    console.log(`Failed to fetch audio file: ${url}`);
  }

  audio["data"] = await response.arrayBuffer();

  // Once we have loaded the sound, see if that was the last one missing
  // and we can get rid of the loading screen.
  checkPendingAssets();
}

// Loads all sounds that were previously registered with registerSound.
function loadSound(sound_id) {
    sound_objects = sounds[sound_id];
    sounds_left = sound_objects.length;

    sound_objects.forEach((sound) => {
        loadAudioBuffer(sound);
    });
}

async function playSound(sound_id, stereo_balance) {
    const sound_assets = sounds[sound_id];

    const index = Math.floor(Math.random() * sound_assets.length);
    const audio = sound_assets[index];

    return await playAudio(audio, stereo_balance);
}

function addPlayer(team_id, row_id, css_class) {
    let row = document.createElement("tr");
    row.id = row_id;
    row.className = css_class;

    columns.forEach((column, index) => {
        let cell = document.createElement("td");
        cell.id = `${row_id}_${index}`;
        row.appendChild(cell);
    });

    document.getElementById(`${team_id}_table`).appendChild(row);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

event_iteration = 0;

function get_playback_speed() {
    return playback_speed;
}

function onSpeedChange() {
    const new_playback_speed = parseFloat(speedText.value);

    if (playback_speed != new_playback_speed) {
        if (play) {
            base_game_time_millis = getCurrentGameTimeMillis();
            base_timestamp = new Date().getTime();
        }

        playback_speed = new_playback_speed;
    }
}

function playEvents() {
    setTimeSlider(getCurrentGameTimeMillis() / 1000);

    for (let i = event_iteration; i < events.length; i++) {
        event_iteration = i;

        if (!play && !scrub) {
            return;
        }

        const event = events[i];
        const timestamp = event[0];

        // check if the event way behind the current time so we don't play audio
        if (timestamp < getCurrentGameTimeMillis() - 1000) {
            recalculating = true;
        } else {
            recalculating = false;
        }

        // check if event is in the future while accounting for speed
        if (timestamp > getCurrentGameTimeMillis()) {
            event_iteration = i;

            if (play) {
                setTimeout(playEvents, 100);
            }
            return;
        }

        oldScrollTop = eventBox.scrollTop + eventBox.clientHeight;
        oldScrollHeight = eventBox.scrollHeight;

        const message = event[1];

        if (message.length > 0) {
            eventBox.innerHTML += `<div class="event">${message}</div>\n`;
        }

        let sortable_column_changed = false;

        // Handle all cell changes.
        event[2].forEach((cell_change) => {
            row_id = cell_change[0];
            column = cell_change[1];
            new_value = cell_change[2];

            document.getElementById(`${row_id}_${column}`).innerHTML = new_value;

            if (sort_columns.includes(parseInt(column))) {
                sortable_column_changed = true;
            }
        });

        if (sortable_column_changed) {
            sortTables();
        }

        // Handle all row changes.
        event[3].forEach((row_change) => {
            row_id = row_change[0];
            css_class = row_change[1];

            document.getElementById(row_id).className = css_class;
        });

        event[4].forEach((team_score, index) => {
            document.getElementById(`${team_ids[index]}_score`).innerHTML = `${team_names[index]}: ${team_score}`;
        });

        const stereo_balance = event[5];

        event[6].forEach((sound_id) => {
            playSound(sound_id, stereo_balance);
        });

        eventBox.scrollTop = eventBox.scrollHeight;
    }
}

// See if there are any pending assets, otherwise start the main UI.
function checkPendingAssets() {
    if (assets_loaded) {
        // We're already all done.
        return;
    }

    missing_assets = false;

    while (missing_sounds.length > 0) {
        const sound_id = missing_sounds[0];
        sounds[sound_id].forEach((sound) => {
            if (!isSoundLoaded(sound)) {
                // Not done yet.
                missing_assets = true;
                return;
            }
        });

        if (missing_assets) {
            // Something still missing. Let's wait.
            return;
        }

        // Everything in this sound is loaded, we can remove it.
        missing_sounds.shift();
    };

    // Everything is loaded. We're good.
    assets_loaded = true;
    enableReplayUi();
}

function enableReplayUi() {
    teamsLoadingPlaceholder.style.display = "none";
    timeSlider.style.display = "flex";
    replayViewer.style.display = "flex";
}

function restartReplay() {
    console.log("Restarting replay");

    if (current_starting_sound_playing != undefined) {
        stopAudio(current_starting_sound_playing);
        current_starting_sound_playing = undefined;
    }

    play = false;
    started = false;
    restarted = true;
    playback_key++;

    // If true, we're not playing back, but we're paused and just want to evaluate the game at a different time.
    scrub = false;

    resetGame();
    playButton.innerHTML = "Play";
    enableReplayUi();
}

function resetGame() {
    eventBox.innerHTML = "";
    event_iteration = 0;
    resetPlayers();
}

function onLoad() {
    teams = document.getElementById("teams");
    replayViewer = document.getElementById("replay_viewer");
    teamsLoadingPlaceholder = document.getElementById("teams_loading_placeholder");
    timeSlider = document.getElementById("time_slider");
    eventBox = document.getElementById("events");
    speedText = document.getElementById("speed");
    playButton = document.getElementById("play");
    restartButton = document.getElementById("restart");

    playButton.addEventListener("click", playPause);
    restartButton.addEventListener("click", restartReplay);

    // initialize the real world timestamp starting at 0
    // so it shows up before we click play.
    setRealWorldTimestampLabel(0);
}

function onTimeChange(seconds) {
    // If the new time is earlier than before, we need to reevaluate everything.
    if (seconds * 1000 < base_game_time_millis) {
        resetGame();
    }

    base_game_time_millis = seconds * 1000
    base_timestamp = new Date().getTime();

    setTimeLabel(seconds);
    setRealWorldTimestampLabel(seconds);

    // If we're not currently playing back, we need to manually update.
    if (!play) {
        scrub = true;
        playEvents();
        scrub = false;
    }
}

function setTimeSlider(seconds) {
    document.getElementById("time-slider").value = seconds;
    setTimeLabel(seconds);
    setRealWorldTimestampLabel(seconds);
}

function setTimeLabel(seconds) {
    const totalSeconds = Math.floor(seconds);

    if (totalSeconds == time_label_seconds) {
        return;
    }

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);

    const formattedMinutes = minutes.toString().padStart(2, "0");
    const formattedSeconds = remainingSeconds.toString().padStart(2, "0");

    document.getElementById("timestamp").innerHTML = `${formattedMinutes}:${formattedSeconds}`;
    time_label_seconds = totalSeconds;
}

function setRealWorldTimestampLabel(seconds) {
    if (start_real_world_timestamp_seconds === null) {
        return;
    }

    new_real_world_timestamp_seconds = start_real_world_timestamp_seconds + Math.floor(seconds);

    if (new_real_world_timestamp_seconds === current_real_world_timestamp_seconds) {
        return;
    }

    current_real_world_timestamp_seconds = new_real_world_timestamp_seconds;

    const date = new Date(current_real_world_timestamp_seconds * 1000); // JavaScript uses milliseconds
    const real_world_time = real_world_timestamp_formatter.format(date);
    document.getElementById("realworld-timestamp").innerHTML = real_world_time;
}

function setIntroSound(soundId) {
    intro_sound = soundId;
}

function setStartSound(soundId) {
    start_sound = soundId;
}

document.addEventListener("DOMContentLoaded", function() {
    onLoad();
});
