

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

started = false;
play = false;
restarted = false;
start_time = 0;

function playPause() {
    if (replay_data == undefined) {
        return;
    }
    if (play) {
        play = false;
        playButton.innerHTML = "Play";
    } else {
        play = true;
        restarted = false;
        playButton.innerHTML = "Pause";
        started = true;
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
        <td><p class="player_codename">${player["name"]}</p></td>
        <td><p class="player_goals">0</p></td>
        <td><p class="player_assists">0</p></td>
        <td><p class="player_steals">0</p></td>
        <td><p class="player_clears">0</p></td>
        <td><p class="player_passes">0</p></td>
        <td><p class="player_blocks">0</p></td>
        <td><p class="player_accuracy">0.00%</p></td>
        `;

        table.appendChild(row);

        player["goals"] = 0;
        player["assists"] = 0;
        player["steals"] = 0;
        player["clears"] = 0;
        player["passes"] = 0;
        player["blocks"] = 0;
        player["downed"] = false;
        player["shots_hit"] = 0;
        player["shots_fired"] = 0;
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

        if (events[i]["type"] != MISS) {
            eventBox.innerHTML += `<p class="event">${updated_arguments.join(" ")}</p>\n`;
        }

        if (oldScrollTop >= oldScrollHeight) {
            eventBox.scrollTop = eventBox.scrollHeight + 100;
        }
        
        if (events[i]["type"] == MISS || events[i]["type"] == MISS_BASE) {
            shooter = getEntityFromId(replay_data, events[i]["arguments"][0]);
            shooter["shots_fired"] += 1;
        }
        else if (events[i]["type"] == PASS) {
            passer = getEntityFromId(replay_data, events[i]["arguments"][0]);
            passer["passes"] += 1;

            passer["shots_fired"] += 1;
            passer["shots_hit"] += 1;
        }
        else if (events[i]["type"] == GOAL) {
            scorer = getEntityFromId(replay_data, events[i]["arguments"][0]);
            scorer["goals"] += 1;

            scorer["shots_fired"] += 1;
            scorer["shots_hit"] += 1;
        }
        else if (events[i]["type"] == STEAL) {
            stealer = getEntityFromId(replay_data, events[i]["arguments"][0]);
            stealer["steals"] += 1;

            stealer["shots_fired"] += 1;
            stealer["shots_hit"] += 1;
        }
        else if (events[i]["type"] == BLOCK) {
            blocker = getEntityFromId(replay_data, events[i]["arguments"][0]);
            blocker["blocks"] += 1;

            blocker["shots_fired"] += 1;
            blocker["shots_hit"] += 1;
        }
        else if (events[i]["type"] == CLEAR) {
            clearer = getEntityFromId(replay_data, events[i]["arguments"][0]);
            clearer["clears"] += 1;

            clearer["shots_fired"] += 1;
            clearer["shots_hit"] += 1;
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

            player["row"].getElementsByTagName("td")[1].getElementsByTagName("p")[0].innerHTML = player["goals"];
            player["row"].getElementsByTagName("td")[2].getElementsByTagName("p")[0].innerHTML = player["assists"];
            player["row"].getElementsByTagName("td")[3].getElementsByTagName("p")[0].innerHTML = player["steals"];
            player["row"].getElementsByTagName("td")[4].getElementsByTagName("p")[0].innerHTML = player["clears"];
            player["row"].getElementsByTagName("td")[5].getElementsByTagName("p")[0].innerHTML = player["passes"];
            player["row"].getElementsByTagName("td")[6].getElementsByTagName("p")[0].innerHTML = player["blocks"];
            player["row"].getElementsByTagName("td")[7].getElementsByTagName("p")[0].innerHTML = accuracy;

            table = player["table"];

            // sort table

            rows = table.getElementsByTagName("tr");

            for (let k = 1; k < rows.length; k++) {
                for (let l = k+1; l < rows.length; l++) {
                    if (parseInt(rows[k].getElementsByTagName("td")[1].getElementsByTagName("p")[0].innerHTML) < parseInt(rows[l].getElementsByTagName("td")[1].getElementsByTagName("p")[0].innerHTML)) {
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

    play = false;
    restarted = true;
    playButton.innerHTML = "Play";
    eventBox.innerHTML = "";
    fireTable.innerHTML = "<tr><th><p>Codename</p></th><th><p>Goals</p></th><th><p>Assists</p></th><th><p>Steals</p></th><th><p>Clears</p></th><th><p>Passes</p></th><th><p>Blocks</p></th><th><p>Accuracy</p></th></tr>";
    earthTable.innerHTML = "<tr><th><p>Codename</p></th><th><p>Goals</p></th><th><p>Assists</p></th><th><p>Steals</p></th><th><p>Clears</p></th><th><p>Passes</p></th><th><p>Blocks</p></th><th><p>Accuracy</p></th></tr>";
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

    fetch("/api/game/lb/" + game_id + "/json")
        .then(response => response.json())
        .then(data => {
            replay_data = data;
            startReplay(replay_data);
        })
}



document.addEventListener("DOMContentLoaded", function() {
    onLoad();
});