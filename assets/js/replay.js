


function playAudio(audio) {
    audio.volume = 0.5;
    if (!recalculating) {
        audio.play();
    }
    return audio;
}

function playDownedAudio() {
    // audio is random between Scream.0.wav Scream.1.wav Scream.2.wav Shot.0.wav Shot.1.wav
    sfx = Math.floor(Math.random() * 5);
    return playAudio(downed_audio[sfx]);
}


start_audio = [new Audio("/assets/sm5/audio/Start.0.wav"), new Audio("/assets/sm5/audio/Start.1.wav"), new Audio("/assets/sm5/audio/Start.2.wav"), new Audio("/assets/sm5/audio/Start.3.wav")];
alarm_start_audio = new Audio("/assets/sm5/audio/Effect/General Quarters.wav");
resupply_audio = [new Audio("/assets/sm5/audio/Effect/Resupply.0.wav"), new Audio("/assets/sm5/audio/Effect/Resupply.1.wav"), new Audio("/assets/sm5/audio/Effect/Resupply.2.wav"), new Audio("/assets/sm5/audio/Effect/Resupply.3.wav"), new Audio("/assets/sm5/audio/Effect/Resupply.4.wav")];
downed_audio = [new Audio("/assets/sm5/audio/Effect/Scream.0.wav"), new Audio("/assets/sm5/audio/Effect/Scream.1.wav"), new Audio("/assets/sm5/audio/Effect/Scream.2.wav"), new Audio("/assets/sm5/audio/Effect/Shot.0.wav"), new Audio("/assets/sm5/audio/Effect/Shot.1.wav")];
base_destroyed_audio = new Audio("/assets/sm5/audio/Effect/Boom.wav");

current_starting_sound_playing = undefined;

started = false;
cancelled_starting_sound = false;
restarted = false;
play = false;
scrub = false; // for when going back in time
recalculating = false; // for when we're mass recalculating and don't want to play audio
playback_speed = 1.0;

columns = [];
team_names = [];
team_ids = [];

// The timestamp (wall clock) when we last started to play back or change the playback settings.
base_timestamp = 0;

// The game time in milliseconds at the time of base_timestamp.
base_game_time_millis = 0;

// The current time being shown in the time label, in seconds.
time_label_seconds = 0;

// Sound IDs and all Audio objects for them.
sounds = {};

/* Returns the time in the game (in milliseconds) that's currently active. */
function getCurrentGameTimeMillis() {
    // If we're not currently playing back, the game time remains unchanged.
    if (!play) {
        return base_game_time_millis;
    }

    const now = new Date().getTime();

    return base_game_time_millis + (now - base_timestamp) * get_playback_speed();
}

function finishedPlayingIntro() {
    if (current_starting_sound_playing != audio || restarted || cancelled_starting_sound) {
        return;
    }
    play = true;
    restarted = false;
    playButton.innerHTML = "Pause";
    started = true;
    base_timestamp = new Date().getTime();
    current_starting_sound_playing = undefined;

    // play the game start sfx
    playAudio(alarm_start_audio);

    playEvents();
}

function playPause() {
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
            resetGame();
            restarted = false;
            finishedPlayingIntro();
            cancelled_starting_sound = true; // cancel the callback for the starting sound
        }
        else if (!started) {
            base_game_time_millis = 0
            // starting the game for the first time

            // choose a random sfx 0-3

            sfx = Math.floor(Math.random() * 4);

            audio = new Audio(`/assets/sm5/audio/Start.${sfx}.wav`);
            audio.volume = 0.5;
            current_starting_sound_playing = audio;
            audio.play();

            audio.addEventListener("loadeddata", () => {
                // wait for the sfx to finish
                setTimeout(function() {
                    finishedPlayingIntro();
                }, audio.duration*1000);
            });
            return;
        }

        play = true;
        playButton.innerHTML = "Pause";
        started = true;
        restarted = false;
        playEvents();
    }
}

function add_column(column_name) {
    columns.push(column_name);
}

function add_team(team_name, team_id, team_css_class) {

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
}

function register_sound(sound_id, asset_urls) {
    sound_objects = [];

    asset_urls.forEach((asset_url) => {
        sound_objects.push(new Audio(asset_url));
    });

    sounds[sound_id] = sound_objects;
}

function play_sound(sound_id) {
    sound_assets = sounds[sound_id];
    index = Math.floor(Math.random() * sound_assets.length);
    audio = sound_assets[index];

    audio.volume = 0.5;
    if (!recalculating) {
        audio.play();
    }
}

function add_player(team_id, row_id, cells) {
    let row = document.createElement("tr");
    row.id = row_id;

    cells.forEach((column, index) => {
        let cell = document.createElement("td");
        cell.id = `${row_id}_${index}`;
        cell.innerHTML = column;
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

        // Handle all cell changes.
        event[2].forEach((cell_change) => {
            row_id = cell_change[0];
            column = cell_change[1];
            new_value = cell_change[2];

            document.getElementById(`${row_id}_${column}`).innerHTML = new_value;
        });

        // Handle all row changes.
        event[3].forEach((row_change) => {
            row_id = row_change[0];
            css_class = row_change[1];

            document.getElementById(row_id).className = css_class;
        });

        event[4].forEach((team_score, index) => {
            document.getElementById(`${team_ids[index]}_score`).innerHTML = `${team_names[index]}: ${team_score}`;
        });

        event[5].forEach((sound_id) => {
            play_sound(sound_id);
        });

        eventBox.scrollTop = eventBox.scrollHeight;
    }
}

function startReplay() {
    teamsLoadingPlaceholder.style.display = "none";
    timeSlider.style.display = "block";
    replayViewer.style.display = "flex";
}

function restartReplay() {
    console.log("Restarting replay");

    if (current_starting_sound_playing != undefined) {
        current_starting_sound_playing.pause();
    }

    play = false;
    started = false;
    restarted = true;

    // If true, we're not playing back, but we're paused and just want to evaluate the game at a different time.
    scrub = false;

    resetGame();
    playButton.innerHTML = "Play";
    startReplay();
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
}

function onTimeChange(seconds) {
    // If the new time is earlier than before, we need to reevaluate everything.
    if (seconds * 1000 < base_game_time_millis) {
        resetGame();
    }

    base_game_time_millis = seconds * 1000
    base_timestamp = new Date().getTime();

    setTimeLabel(seconds);

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

document.addEventListener("DOMContentLoaded", function() {
    onLoad();
});
