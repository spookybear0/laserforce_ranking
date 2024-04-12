

commander_defaults = {
    name: "commander",
    lives: 15,
    lives_resupply: 4,
    lives_max: 30,
    shots: 30,
    shots_resupply: 5,
    shots_max: 60,
    missiles: 5
};

heavy_defaults = {
    name: "heavy",
    lives: 10,
    lives_resupply: 3,
    lives_max: 20,
    shots: 20,
    shots_resupply: 5,
    shots_max: 40,
    missiles: 5
};

scout_defaults = {
    name: "scout",
    lives: 15,
    lives_resupply: 5,
    lives_max: 30,
    shots: 30,
    shots_resupply: 10,
    shots_max: 60,
    missiles: 0
};

ammo_defaults = {
    name: "ammo",
    lives: 10,
    lives_resupply: 3,
    lives_max: 20,
    shots: 15,
    shots_resupply: 0,
    shots_max: 15,
    missiles: 0
};

medic_defaults = {
    name: "medic",
    lives: 20,
    lives_resupply: 0,
    lives_max: 20,
    shots: 15,
    shots_resupply: 5,
    shots_max: 30,
    missiles: 0
};

// audio files
// TODO: make it so the same audio file can be played multiple times at once

start_audio = [new Audio("/assets/sm5/audio/Start.0.wav"), new Audio("/assets/sm5/audio/Start.1.wav"), new Audio("/assets/sm5/audio/Start.2.wav"), new Audio("/assets/sm5/audio/Start.3.wav")];
alarm_start_audio = new Audio("/assets/sm5/audio/Effect/General Quarters.wav");
resupply_audio = [new Audio("/assets/sm5/audio/Effect/Resupply.0.wav"), new Audio("/assets/sm5/audio/Effect/Resupply.1.wav"), new Audio("/assets/sm5/audio/Effect/Resupply.2.wav"), new Audio("/assets/sm5/audio/Effect/Resupply.3.wav"), new Audio("/assets/sm5/audio/Effect/Resupply.4.wav")];
downed_audio = [new Audio("/assets/sm5/audio/Effect/Scream.0.wav"), new Audio("/assets/sm5/audio/Effect/Scream.1.wav"), new Audio("/assets/sm5/audio/Effect/Scream.2.wav"), new Audio("/assets/sm5/audio/Effect/Shot.0.wav"), new Audio("/assets/sm5/audio/Effect/Shot.1.wav")];
base_destroyed_audio = new Audio("/assets/sm5/audio/Effect/Boom.wav");

// Event codes

var MISSION_START = 100;
var MISSION_END = 101;
var SHOT_EMPTY = 200; // unused?
var MISS = 201;
var MISS_BASE = 202;
var HIT_BASE = 203;
var DESTROY_BASE = 204;
var DAMAGED_OPPONENT = 205;
var DOWNED_OPPONENT = 206;
var DAMANGED_TEAM = 207; // unused?
var DOWNED_TEAM = 208; // unused?
var LOCKING = 300; // (aka missile start)
var MISSILE_BASE_MISS = 301;
var MISSILE_BASE_DAMAGE = 302;
var MISISLE_BASE_DESTROY = 303;
var MISSILE_MISS = 304;
var MISSILE_DAMAGE_OPPONENT = 305; // unused? theres no way for a missile to not down/destroy
var MISSILE_DOWN_OPPONENT = 306;
var MISSILE_DAMAGE_TEAM = 307; // unused? ditto
var MISSILE_DOWN_TEAM = 308;
var ACTIVATE_RAPID_FIRE = 400;
var DEACTIVATE_RAPID_FIRE = 401; // unused?
var ACTIVATE_NUKE = 404;
var DETONATE_NUKE = 405;
var RESUPPLY_AMMO = 500;
var RESUPPLY_LIVES = 502;
var AMMO_BOOST = 510;
var LIFE_BOOST = 512;
var PENALTY = 600;
var ACHIEVEMENT = 900;
var BASE_AWARDED = 2819; // (technically #0B03 in hex)

var PASS = 1100;
var GOAL = 1101;
var STEAL = 1103;
var BLOCK = 1104;
var ROUND_START = 1105;
var ROUND_END = 1106;
var GETS_BALL = 1107;
var CLEAR = 1108;

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

replay_data = undefined;

current_starting_sound_playing = undefined;

started = false;
cancelled_starting_sound = false;
restarted = false;
play = false;
scrub = false; // for when going back in time
recalculating = false; // for when we're mass recalculating and don't want to play audio
playback_speed = 1.0;

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

    playEvents(replay_data);
}

function playPause() {
    if (replay_data == undefined) {
        return;
    }

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
        playEvents(replay_data);
    }
}

function getTeamFromId(replay_data, id) {
    for (let i = 0; i < replay_data["teams"].length; i++) {
        if (replay_data["teams"][i]["index"] == id) {
            return replay_data["teams"][i];
        }
    }
}

function getEntityFromId(replay_data, entity_id) {
    for (let i = 0; i < replay_data["entity_starts"].length; i++) {
        if (replay_data["entity_starts"][i]["entity_id"] == entity_id) {
            return replay_data["entity_starts"][i];
        }
    }
}


function getDefaults(role) {
    if (role == 1) {
        return commander_defaults;
    } else if (role == 2) {
        return heavy_defaults;
    } else if (role == 3) {
        return scout_defaults;
    } else if (role == 4) {
        return ammo_defaults;
    } else if (role == 5) {
        return medic_defaults;
    }
}


function setupGame(replay_data) {
    // loop over all players in enitity_start

    for (let i = 0; i < replay_data["entity_starts"].length; i++) {
        let player = replay_data["entity_starts"][i];

        if (player["type"] != "player") {
            continue;
        }

        team = getTeamFromId(replay_data, player["team"]);

        team_color_name = "orangered";

        if (team["color_name"] == "Fire") {
            table = fireTable;
            team_color_name = "orangered";
        } else {
            table = earthTable;
            team_color_name = "greenyellow";
        }

        role = player["role"];

        defaults = getDefaults(role);

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

function playEvents(replay_data) {
    let events = replay_data["events"];

    setTimeSlider(getCurrentGameTimeMillis() / 1000);

    for (let i = event_iteration; i < events.length; i++) {
        event_iteration = i;

        if (!play && !scrub) {
            return;
        }

        // check if the event way behind the current time so we don't play audio
        if (events[i]["time"] < getCurrentGameTimeMillis() - 1000) {
            recalculating = true;
        } else {
            recalculating = false;
        }

        events[i]["type"] = parseInt(events[i]["type"]);

        // check if event is in the future while accounting for speed
        if (events[i]["time"] > getCurrentGameTimeMillis()) {
            event_iteration = i;

            if (play) {
                setTimeout(playEvents, 100, replay_data);
            }
            return;
        }

        updated_arguments = [];

        for (let j = 0; j < events[i]["arguments"].length; j++) {
            if (events[i]["arguments"][j].startsWith("@")) {
                updated_arguments.push(`<span>${getEntityFromId(replay_data, events[i]["arguments"][j])["name"]}</span>`);
            }
            else if (events[i]["arguments"][j].startsWith("#")) {
                // get team then change color to team color
                entity = getEntityFromId(replay_data, events[i]["arguments"][j])["name"]

                team = getTeamFromId(replay_data, getEntityFromId(replay_data, events[i]["arguments"][j])["team"]);
                if (team["color_name"] == "Fire") {
                    entity = `<span style="color: orangered;">${entity}</span>`;
                }
                else {
                    entity = `<span style="color: greenyellow;">${entity}</span>`;
                }

                updated_arguments.push(entity);
            }
            else {
                updated_arguments.push(`<span>${events[i]["arguments"][j].trim()}</span>`);
            }
        }

        oldScrollTop = eventBox.scrollTop + eventBox.clientHeight;
        oldScrollHeight = eventBox.scrollHeight;
        
        if (events[i]["type"] != MISS) {
            eventBox.innerHTML += `<div class="event">${updated_arguments.join(" ")}</div>\n`;
        }

        if (events[i]["type"] == MISS || events[i]["type"] == MISS_BASE) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["shots_fired"] += 1;
            if (shooter["role"] != 4) { // not ammo
                shooter["shots"] -= 1;
            }
        }
        else if (events[i]["type"] == HIT_BASE) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["shots_fired"] += 1;
            shooter["shots_hit"] += 1;
            if (shooter["role"] != 4) { // not ammo
                shooter["shots"] -= 1;
            }
        }
        else if (events[i]["type"] == DESTROY_BASE) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["shots_fired"] += 1;
            shooter["shots_hit"] += 1;
            if (shooter["role"] != 4) { // not ammo
                shooter["shots"] -= 1;
            }
            if (shooter["role"] != 2 || shooter["rapid_fire"]) { // not heavy:
                shooter["special_points"] += 5;
            }
            shooter["score"] += 1001;

            playAudio(base_destroyed_audio);
        }
        else if (events[i]["type"] == DAMAGED_OPPONENT) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["shots_fired"] += 1;
            shooter["shots_hit"] += 1;
            if (shooter["role"] != 4) { // not ammo
                shooter["shots"] -= 1;
            }
            if (shooter["role"] != 2 || shooter["rapid_fire"]) { // not heavy:
                shooter["special_points"] += 1;
            }
            shooter["score"] += 100;

            victim = getEntityFromId(replay_data, events[i]["arguments"][2]);
            victim["score"] -= 20;
            victim["times_shot"] += 1;

            playDownedAudio();
        }
        else if (events[i]["type"] == DOWNED_OPPONENT) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["shots_fired"] += 1;
            shooter["shots_hit"] += 1;
            if (shooter["role"] != 4) { // not ammo
                shooter["shots"] -= 1;
            }
            if (shooter["role"] != 2 || shooter["rapid_fire"]) { // not heavy:
                shooter["special_points"] += 1;
            }
            shooter["score"] += 100;

            victim = getEntityFromId(replay_data, events[i]["arguments"][2]);
            victim["score"] -= 20;
            if (victim["lives"] > 0) {
                victim["lives"] -= 1
            }
            victim["times_shot"] += 1;
            victim["downed"] = true;
            setTimeout(function() {
                victim["downed"] = false;
            }, 8000 * get_playback_speed());

            playDownedAudio();
        }
        else if (events[i]["type"] == DAMANGED_TEAM) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["shots_fired"] += 1;
            shooter["shots_hit"] += 1;
            if (shooter["role"] != 4) { // not ammo
                shooter["shots"] -= 1;
            }
            shooter["score"] -= 100;

            victim = getEntityFromId(replay_data, events[i]["arguments"][2]);
            victim["score"] -= 20;
            victim["times_shot"] += 1;

            playDownedAudio(); // TODO: find the sound for shooting a teammate
        }
        else if (events[i]["type"] == DOWNED_TEAM) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["shots_fired"] += 1;
            shooter["shots_hit"] += 1;
            if (shooter["role"] != 4) { // not ammo
                shooter["shots"] -= 1;
            }
            shooter["score"] -= 100;

            victim = getEntityFromId(replay_data, events[i]["arguments"][2]);
            victim["score"] -= 20;

            if (victim["lives"] > 0) {
                victim["lives"] -= 1;
            }
            victim["times_shot"] += 1;

            victim["downed"] = true;
            setTimeout(function() {
                victim["downed"] = false;
            }, 8000 * get_playback_speed());

            playDownedAudio(); // TODO: find the sound for shooting a teammate
        }
        else if (events[i]["type"] == MISSILE_BASE_MISS || events[i]["type"] == MISSILE_MISS) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["missiles"] -= 1;
        }
        else if (events[i]["type"] == MISISLE_BASE_DESTROY || events[i]["type"] == MISSILE_BASE_DAMAGE) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["missiles"] -= 1;
            if (shooter["role"] != 2 || shooter["rapid_fire"]) { // not heavy
                shooter["special_points"] += 5;
            }
            shooter["score"] += 1001;

            playAudio(base_destroyed_audio);
        }
        else if (events[i]["type"] == MISSILE_DOWN_OPPONENT || events[i]["type"] == MISSILE_DAMAGE_OPPONENT) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["missiles"] -= 1
            if (shooter["role"] != 2 || shooter["rapid_fire"]) { // not heavy
                shooter["special_points"] += 2
            }
            shooter["score"] += 500

            victim = getEntityFromId(replay_data, events[i]["arguments"][2]);
            victim["score"] -= 100
            victim["lives"] -= 2
            victim["downed"] = true;
            setTimeout(function() {
                victim["downed"] = false;
            }, 8000 * get_playback_speed());

            playDownedAudio(); // TODO: find the sound for missiling a player
        }
        else if (events[i]["type"] == MISSILE_DOWN_TEAM || events[i]["type"] == MISSILE_DAMAGE_TEAM) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["missiles"] -= 1;
            shooter["score"] -= 500;

            victim = getEntityFromId(replay_data, events[i]["arguments"][2]);
            victim["score"] -= 100;
            victim["lives"] -= 2;
            victim["downed"] = true;
            setTimeout(function() {
                victim["downed"] = false;
            }, 8000 * get_playback_speed());

            playDownedAudio(); // TODO: find the sound for missiling a teammate/missiling a player
        }
        else if (events[i]["type"] == ACTIVATE_RAPID_FIRE) {
            player = getEntityFromId(replay_data, events[i]["arguments"][0]);
            player["special_points"] -= 10;
            player["rapid_fire"] = true;

            eventBox.innerHTML += `<p class="event">${player["name"]} activates rapid fire</p>\n`;

            // TODO: find the sound for activating rapid fire
        }
        else if (events[i]["type"] == DEACTIVATE_RAPID_FIRE) {
            player = getEntityFromId(replay_data, events[i]["arguments"][0]);
            player["rapid_fire"] = false;
            eventBox.innerHTML += `<p class="event">${player["name"]} deactivates rapid fire</p>\n`;
        }
        else if (events[i]["type"] == ACTIVATE_NUKE) {
            nuker = getEntityFromId(replay_data, events[i]["arguments"][0]);
            nuker["special_points"] -= 20;

            // TODO: find the sound for activating nuke
        }
        else if (events[i]["type"] == DETONATE_NUKE) {
            nuker = getEntityFromId(replay_data, events[i]["arguments"][0]);

            for (let j = 0; j < replay_data["entity_starts"].length; j++) {
                player = replay_data["entity_starts"][j];
                if (player["team"] != nuker["team"] && player["type"] == "player") {
                    player["downed"] = true;
                    setTimeout(function() {
                        player["downed"] = false;
                    }, 8000 * get_playback_speed());

                    if (player["lives"] < 3) {
                        player["lives"] = 0;
                    }
                    else {
                        player["lives"] -= 3;
                    }
                }
            }

            nuker["score"] += 500;

            // TODO: find the sound for detonating nuke
        }
        else if (events[i]["type"] == RESUPPLY_AMMO) {
            resupplyee = getEntityFromId(replay_data, events[i]["arguments"][2]);
            defaults = getDefaults(resupplyee["role"]);

            resupplyee["shots"] += defaults["shots_resupply"];
            if (resupplyee["shots"] > defaults["shots_max"]) {
                resupplyee["shots"] = defaults["shots_max"];
            }

            resupplyee["downed"] = true;
            setTimeout(function() {
                resupplyee["downed"] = false;
            }, 8000 * get_playback_speed());
            
            resupplyee["rapid_fire"] = false;

            // get random sound for resupplying Resupply.0-4.wav

            sfx = Math.floor(Math.random() * 5);
            playAudio(resupply_audio[sfx]);
        }
        else if (events[i]["type"] == RESUPPLY_LIVES) {
            resupplyee = getEntityFromId(replay_data, events[i]["arguments"][2]);
            defaults = getDefaults(resupplyee["role"]);

            resupplyee["lives"] += defaults["lives_resupply"];
            if (resupplyee["lives"] > defaults["lives_max"]) {
                resupplyee["lives"] = defaults["lives_max"];
            }

            resupplyee["downed"] = true;
            setTimeout(function() {
                resupplyee["downed"] = false;
            }, 8000 * get_playback_speed());
            
            resupplyee["rapid_fire"] = false;

            // get random sound for resupplying Resupply.0-4.wav

            sfx = Math.floor(Math.random() * 5);
            playAudio(resupply_audio[sfx]);
        }
        else if (events[i]["type"] == AMMO_BOOST) {
            booster = getEntityFromId(replay_data, events[i]["arguments"][0]);

            for (let j = 0; j < replay_data["entity_starts"].length; j++) {
                player = replay_data["entity_starts"][j];
                if (player["team"] == booster["team"] && player["type"] == "player" && !player["downed"]) {
                    defaults = getDefaults(player["role"])
                    player["shots"] += defaults["shots_resupply"];
                    if (player["shots"] > defaults["shots_max"]) {
                        player["shots"] = defaults["shots_max"];
                    }
                }
            }

            // get random sound for resupplying Resupply.0-4.wav

            sfx = Math.floor(Math.random() * 5);
            playAudio(resupply_audio[sfx]);
        }
        else if (events[i]["type"] == LIFE_BOOST) {
            booster = getEntityFromId(replay_data, events[i]["arguments"][0]);

            for (let j = 0; j < replay_data["entity_starts"].length; j++) {
                player = replay_data["entity_starts"][j];
                if (player["team"] == booster["team"] && player["type"] == "player" && !player["downed"]) {
                    defaults = getDefaults(player["role"])
                    player["lives"] += defaults["lives_resupply"];
                    if (player["lives"] > defaults["lives_max"]) {
                        player["lives"] = defaults["lives_max"];
                    }
                }
            }

            // get random sound for resupplying Resupply.0-4.wav

            sfx = Math.floor(Math.random() * 5);
            playAudio(resupply_audio[sfx]);
        }
        else if (events[i]["type"] == PENALTY) {
            penaltyee = getEntityFromId(replay_data, events[i]["arguments"][2]);
            penaltyee["score"] -= 1000;
        }

        for (let j = 0; j < replay_data["entity_starts"].length; j++) {
            player = replay_data["entity_starts"][j];

            if (player["type"] != "player") {
                continue;
            }

            defaults = getDefaults(player["role"]);

            if (player["shots_fired"] == 0) {
                accuracy = "0.00%";
            }
            else {
                accuracy = (player["shots_hit"]/player["shots_fired"]*100).toFixed(2) + "%";
            }

            if (player["times_shot"] == 0) {
                kd = "0.00";
            }
            else {
                kd = (player["shots_hit"]/player["times_shot"]).toFixed(2);
            }

            player["row"].getElementsByTagName("td")[2].getElementsByTagName("p")[0].innerHTML = player["score"];
            player["row"].getElementsByTagName("td")[3].getElementsByTagName("p")[0].innerHTML = player["lives"];
            player["row"].getElementsByTagName("td")[4].getElementsByTagName("p")[0].innerHTML = player["shots"];
            player["row"].getElementsByTagName("td")[5].getElementsByTagName("p")[0].innerHTML = player["missiles"];
            player["row"].getElementsByTagName("td")[6].getElementsByTagName("p")[0].innerHTML = player["special_points"];
            player["row"].getElementsByTagName("td")[7].getElementsByTagName("p")[0].innerHTML = accuracy;
            player["row"].getElementsByTagName("td")[8].getElementsByTagName("p")[0].innerHTML = kd;

            table = player["table"];

            // sort table

            rows = table.getElementsByTagName("tr");

            for (let k = 1; k < rows.length; k++) {
                for (let l = k+1; l < rows.length; l++) {
                    if (parseInt(rows[k].getElementsByTagName("td")[2].getElementsByTagName("p")[0].innerHTML) < parseInt(rows[l].getElementsByTagName("td")[2].getElementsByTagName("p")[0].innerHTML)) {
                        table.insertBefore(rows[l], rows[k]);
                    }
                }
            }

            // check if player is downed

            color = player["row"].getElementsByTagName("td")[1].getElementsByTagName("p")[0].style.color;
            
            if (player["downed"]) {
                if (color == "orangered") {
                    player["row"].getElementsByTagName("td")[1].getElementsByTagName("p")[0].style.color = "#802200";
                }
                else if (color == "greenyellow") {
                    player["row"].getElementsByTagName("td")[1].getElementsByTagName("p")[0].style.color = "#4d8000";
                }
            }
            else {
                if (color == "rgb(128, 34, 0)") {
                    player["row"].getElementsByTagName("td")[1].getElementsByTagName("p")[0].style.color = "orangered";
                }
                else if (color == "rgb(77, 128, 0)") {
                    player["row"].getElementsByTagName("td")[1].getElementsByTagName("p")[0].style.color = "greenyellow";
                }
            }
        }

        eventBox.scrollTop = eventBox.scrollHeight;

        // team scores

        fireScore = 0;
        earthScore = 0;

        for (let j = 0; j < replay_data["entity_starts"].length; j++) {
            player = replay_data["entity_starts"][j];

            if (player["type"] != "player") {
                continue;
            }

            if (player["team"] == 0) {
                fireScore += player["score"];
            }
            else {
                earthScore += player["score"];
            }
        }

        document.getElementById("fire_team_score").innerHTML = `Fire Team: ${fireScore}`;
        document.getElementById("earth_team_score").innerHTML = `Earth Team: ${earthScore}`;
    }
}

function startReplay(replay_data) {
    teamsLoadingPlaceholder.style.display = "none";
    timeSlider.style.display = "block";
    replayViewer.style.display = "flex";

    setupGame(replay_data);
}

function restartReplay() {
    console.log("Restarting replay");

    if (replay_data == undefined) {
        return;
    }

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
    startReplay(replay_data);
}

function resetGame() {
    eventBox.innerHTML = "";
    event_iteration = 0;
    fireTable.innerHTML = "<tr><th><p>Role</p></th><th><p>Codename</p></th><th><p>Score</p></th><th><p>Lives</p></th><th><p>Shots</p></th><th><p>Missiles</p></th><th><p>Spec</p></th><th><p>Accuracy</p></th></tr>";
    earthTable.innerHTML = "<tr><th><p>Role</p></th><th><p>Codename</p></th><th><p>Score</p></th><th><p>Lives</p></th><th><p>Shots</p></th><th><p>Missiles</p></th><th><p>Spec</p></th><th><p>Accuracy</p></th></tr>";
}

function onLoad() {
    fireTable = document.getElementById("fire_table");
    earthTable = document.getElementById("earth_table");
    replayViewer = document.getElementById("replay_viewer");
    teamsLoadingPlaceholder = document.getElementById("teams_loading_placeholder");
    timeSlider = document.getElementById("time_slider");
    eventBox = document.getElementById("events");
    speedText = document.getElementById("speed");
    playButton = document.getElementById("play");
    restartButton = document.getElementById("restart");

    playButton.addEventListener("click", playPause);
    restartButton.addEventListener("click", restartReplay);

    // get the replay data from api using a get request

    fetch("/api/game/sm5/" + game_id + "/json")
        .then(response => response.json())
        .then(data => {
            replay_data = data;
            startReplay(replay_data);
        })
}

function onTimeChange(seconds) {
    // If the new time is earlier than before, we need to reevaluate everything.
    if (seconds * 1000 < base_game_time_millis) {
        resetGame();
        setupGame(replay_data);
    }

    base_game_time_millis = seconds * 1000
    base_timestamp = new Date().getTime();

    setTimeLabel(seconds);

    // If we're not currently playing back, we need to manually update.
    if (!play) {
        scrub = true;
        playEvents(replay_data);
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
