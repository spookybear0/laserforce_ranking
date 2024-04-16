


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

current_starting_sound_playing = undefined;

started = false;
cancelled_starting_sound = false;
restarted = false;
play = false;
scrub = false; // for when going back in time
recalculating = false; // for when we're mass recalculating and don't want to play audio
playback_speed = 1.0;

columns = [];

// The timestamp (wall clock) when we last started to play back or change the playback settings.
base_timestamp = 0;

// The game time in milliseconds at the time of base_timestamp.
base_game_time_millis = 0;

// The current time being shown in the time label, in seconds.
time_label_seconds = 0;

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
    console
    if (current_starting_sound_playing != audio || restarted || cancelled_starting_sound) {
        return;
    }
    play = true;
    restarted = false;
    playButton.innerHTML = "Pause";
    started = true;
    base_timestamp = new Date().getTime();

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
            restartReplay();
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
    teams.innerHTML +=
        "<table>" +
        "<tr><th ><p>Role</p></th><th><p>Codename</p></th><th><p>Score</p></th><th><p>Lives</p></th><th><p>Shots</p></th><th><p>Missiles</p></th><th><p>Spec</p></th><th><p>Accuracy</p><th><p>K/D</p></th></tr>" +
        "</table>";
}

function add_player(player_name) {
    row = document.createElement("tr");

    row.innerHTML =
    `
    `;

//    table.appendChild(row);

}

function setupGame() {
    // loop over all players in enitity_start
    return;

    row = document.createElement("tr");

    row.innerHTML =
    `
    <td><img src="/assets/sm5/roles/${defaults["name"]}.png" alt="role image" width="30" height="30"></td>
    <td><p class="player_codename" style="color: ${team_color_name};">${player["name"]}</p></td>
    <td><p class="player_score">0</p></td>
    <td><p class="player_lives">${defaults["lives"]}</p></td>
    <td><p class="player_shots">${defaults["shots"]}</p></td>
    <td><p class="player_missiles">${defaults["missiles"]}</p></td>
    <td><p class="player_special_points">0</p></td>
    <td><p class="player_accuracy">0.00%</p></td>
    <td><p class="player_kd">0.00</p></td>
    `;

    table.appendChild(row);

    player["lives"] = defaults["lives"];
    player["shots"] = defaults["shots"];
    player["missiles"] = defaults["missiles"];
    player["downed"] = false;
    player["special_points"] = 0;
    player["shots_hit"] = 0;
    player["shots_fired"] = 0;
    player["score"] = 0;
    player["rapid_fire"] = false;
    player["times_shot"] = 0;
    player["row"] = row;
    player["table"] = table;
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

        eventBox.scrollTop = eventBox.scrollHeight;
    }
}

function startReplay() {
    teamsLoadingPlaceholder.style.display = "none";
    timeSlider.style.display = "block";
    replayViewer.style.display = "flex";

    setupGame();
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
    teams.innerHTML = "";
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
        setupGame();
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
