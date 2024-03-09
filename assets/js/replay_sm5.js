

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

replay_data = undefined;

current_sound_playing = undefined;

started = false;
restarted = false;
play = false;
start_time = 0;

function playPause() {
    if (replay_data == undefined) {
        return;
    }

    if (play) {
        play = false;
        playButton.innerHTML = "Play";
    } else {
        restarted = false;
        if (!started) {
            // starting the game for the first time
            
            // choose a random sfx 0-3

            sfx = Math.floor(Math.random() * 4);

            audio = new Audio(`/assets/sm5/audio/Start.${sfx}.wav`);
            current_sound_playing = audio;
            audio.play();

            audio.addEventListener("loadeddata", () => {
                // wait for the sfx to finish
                setTimeout(function() {
                    if (current_sound_playing != audio || restarted) {
                        return;
                    }
                    play = true;
                    restarted = false;
                    playButton.innerHTML = "Pause";
                    started = true;
                    start_time = new Date().getTime();
                    playEvents(replay_data);
                }, audio.duration*1000);
            });
            return;
        }

        play = true;
        playButton.innerHTML = "Pause";
        started = true;
        restarted = false;
        start_time = new Date().getTime();
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

        if (team["color_name"] == "Fire") {
            table = fireTable;
        } else {
            table = earthTable;
        }

        role = player["role"];

        defaults = getDefaults(role);

        row = document.createElement("tr");

        row.innerHTML = 
        `
        <td><img src="/assets/sm5/roles/${defaults["name"]}.png" alt="role image" width="30" height="30"></td>
        <td><p class="player_codename">${player["name"]}</p></td>
        <td><p class="player_score">0</p></td>
        <td><p class="player_lives">${defaults["lives"]}</p></td>
        <td><p class="player_shots">${defaults["shots"]}</p></td>
        <td><p class="player_missiles">${defaults["missiles"]}</p></td>
        <td><p class="player_special_points">0</p></td>
        <td><p class="player_accuracy">0.00%</p></td>
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
        player["row"] = row;
        player["table"] = table;
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

event_iteration = 0;

function playEvents(replay_data) {
    let events = replay_data["events"];

    for (let i = event_iteration; i < events.length; i++) {
        event_iteration = i;

        if (!play) {
            return;
        }

        events[i]["type"] = parseInt(events[i]["type"]);

        // check if event is in the future while accounting for speed
        if (events[i]["time"] > (new Date().getTime() - start_time)*parseFloat(speedText.value)) {
            event_iteration = i;
            setTimeout(playEvents, 100, replay_data);
            return;
        }

        updated_arguments = [];

        for (let j = 0; j < events[i]["arguments"].length; j++) {
            if (events[i]["arguments"][j].startsWith("@") || events[i]["arguments"][j].startsWith("#")) {
                updated_arguments.push(getEntityFromId(replay_data, events[i]["arguments"][j])["name"]);
            }
            else {
                updated_arguments.push(events[i]["arguments"][j]);
            }
        }

        oldScrollTop = eventBox.scrollTop + eventBox.clientHeight;
        oldScrollHeight = eventBox.scrollHeight;

        eventBox.innerHTML += `<p class="event">${updated_arguments.join(" ")}</p>\n`;

        if (oldScrollTop >= oldScrollHeight) {
            eventBox.scrollTop = eventBox.scrollHeight + 100;
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
        }
        else if (events[i]["type"] == MISSILE_DOWN_TEAM || events[i]["type"] == MISSILE_DAMAGE_TEAM) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["missiles"] -= 1;
            shooter["score"] -= 500;

            victim = getEntityFromId(replay_data, events[i]["arguments"][2]);
            victim["score"] -= 100;
            victim["lives"] -= 2;
        }
        else if (events[i]["type"] == ACTIVATE_RAPID_FIRE) {
            player = getEntityFromId(replay_data, events[i]["arguments"][0]);
            player["special_points"] -= 10;
            player["rapid_fire"] = true;
        }
        else if (events[i]["type"] == DEACTIVATE_RAPID_FIRE) {
            player = getEntityFromId(replay_data, events[i]["arguments"][0]);
            player["rapid_fire"] = false;
            eventBox.innerHTML += `<p class="event">${player["name"]} deactivates rapid fire</p>\n`;
        }
        else if (events[i]["type"] == ACTIVATE_NUKE) {
            nuker = getEntityFromId(replay_data, events[i]["arguments"][0]);
            nuker["special_points"] -= 20;
        }
        else if (events[i]["type"] == DETONATE_NUKE) {
            nuker = getEntityFromId(replay_data, events[i]["arguments"][0]);

            for (let j = 0; j < replay_data["entity_starts"].length; j++) {
                player = replay_data["entity_starts"][j];
                if (player["team"] != nuker["team"] && player["type"] == "player") {
                    if (player["lives"] < 3) {
                        player["lives"] = 0;
                    }
                    else {
                        player["lives"] -= 3;
                    }
                }
            }

            nuker["score"] += 500;
        }
        else if (events[i]["type"] == RESUPPLY_AMMO) {
            resupplyee = getEntityFromId(replay_data, events[i]["arguments"][2]);
            defaults = getDefaults(resupplyee["role"]);

            resupplyee["shots"] += defaults["shots_resupply"];
            if (resupplyee["shots"] > defaults["shots_max"]) {
                resupplyee["shots"] = defaults["shots_max"];
            }
            
            resupplyee["rapid_fire"] = false;
        }
        else if (events[i]["type"] == RESUPPLY_LIVES) {
            resupplyee = getEntityFromId(replay_data, events[i]["arguments"][2]);
            defaults = getDefaults(resupplyee["role"]);

            resupplyee["lives"] += defaults["lives_resupply"];
            if (resupplyee["lives"] > defaults["lives_max"]) {
                resupplyee["lives"] = defaults["lives_max"];
            }
            
            resupplyee["rapid_fire"] = false;
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

            player["row"].getElementsByTagName("td")[2].getElementsByTagName("p")[0].innerHTML = player["score"];
            player["row"].getElementsByTagName("td")[3].getElementsByTagName("p")[0].innerHTML = player["lives"];
            player["row"].getElementsByTagName("td")[4].getElementsByTagName("p")[0].innerHTML = player["shots"];
            player["row"].getElementsByTagName("td")[5].getElementsByTagName("p")[0].innerHTML = player["missiles"];
            player["row"].getElementsByTagName("td")[6].getElementsByTagName("p")[0].innerHTML = player["special_points"];
            player["row"].getElementsByTagName("td")[7].getElementsByTagName("p")[0].innerHTML = accuracy;

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
        }
    }
}

function startReplay(replay_data) {
    console.log("Starting replay");

    setupGame(replay_data);
}

function restartReplay() {
    console.log("Restarting replay");

    if (replay_data == undefined) {
        return;
    }

    if (current_sound_playing != undefined) {
        current_sound_playing.pause();
    }

    play = false;
    started = false;
    restarted = true;
    playButton.innerHTML = "Play";
    eventBox.innerHTML = "";
    fireTable.innerHTML = "<tr><th><p>Role</p></th><th><p>Codename</p></th><th><p>Score</p></th><th><p>Lives</p></th><th><p>Shots</p></th><th><p>Missiles</p></th><th><p>Spec</p></th><th><p>Accuracy</p></th></tr>";
    earthTable.innerHTML = "<tr><th><p>Role</p></th><th><p>Codename</p></th><th><p>Score</p></th><th><p>Lives</p></th><th><p>Shots</p></th><th><p>Missiles</p></th><th><p>Spec</p></th><th><p>Accuracy</p></th></tr>";
    event_iteration = 0;
    startReplay(replay_data);
}

function onLoad() {
    fireTable = document.getElementById("fire_team");
    earthTable = document.getElementById("earth_team");
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



document.addEventListener("DOMContentLoaded", function() {
    onLoad();
});