

function addTeam() {
    if (numTeams < 4) {
        numTeams++;
        document.getElementById("team" + numTeams + "-div").style.display = "block";

        if (numTeams > 2) {
            document.getElementById("team1-div").style.height = "45%";
            document.getElementById("team2-div").style.height = "45%";
            document.getElementById("team3-div").style.height = "45%";
            document.getElementById("team4-div").style.height = "45%";
        }
    }
}

function removeTeam() {
    if (numTeams > 2) {
        document.getElementById("team" + numTeams + "-div").style.display = "none";
        numTeams--;

        if (numTeams < 3) {
            document.getElementById("team1-div").style.height = "100%";
            document.getElementById("team2-div").style.height = "100%";
        }
    }
}

// letters are used to sort the table descending
function sortTable(table) {
    let rows, switching, i, x, y, shouldSwitch;
    switching = true;

    while (switching) {
        switching = false;
        rows = table.rows;

        for (i = 1; i < (rows.length - 1); i++) {
            shouldSwitch = false;
            x = rows[i].getElementsByTagName("TD")[0];
            y = rows[i + 1].getElementsByTagName("TD")[0];

            if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                shouldSwitch = true;
                break;
            }
        }

        if (shouldSwitch) {
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
        }
    }
}

function dragEnd(event, target_=undefined) {
    // find the team div that the player was dropped into (which team div is the closest to the mouse position)
    let droppedDiv = document.elementFromPoint(event.clientX, event.clientY);
    let teamTable;

    if (target_ != undefined) {
        target = target_;
    }
    else {
        target = event.target;
    }

    if (target.tagName == "TD") {
        target = target.parentElement;
    }

    if (target.tagName == undefined || target.tagName == "TH" || target.tagName == "TD") {
        return;
    }

    if (!droppedDiv) {
        return;
    }

    if (droppedDiv.classList.contains("team-div") || droppedDiv.classList.contains("players-div")) {
        teamTable = droppedDiv.querySelector("table").querySelector("tbody");
    }
    else if (droppedDiv.tagName == "TR") {
        teamTable = droppedDiv.parentElement;
    }
    else if (droppedDiv.tagName == "TD" || droppedDiv.tagName == "TH") {
        teamTable = droppedDiv.parentElement.parentElement;
    }
    else if (droppedDiv.tagName == "TABLE") {
        teamTable = droppedDiv;
    }
    else {
        return;
    }

    droppedDiv = teamTable.parentElement.parentElement;

    // if the team div is not the same as the one the player was dragged from, add the player to the team div
    if (droppedDiv.querySelector("table").querySelector("tbody") != target.parentElement) {
        teamTable.innerHTML += '<tr draggable="true" ondragend="dragEnd(event)">' + target.innerHTML + "</tr>";
        target.remove();
    }

    sortTable(teamTable);
    updateWinChances();

    event.preventDefault();
}

// if on mobile, allow clicking to select, then clicking again to drop
function onClick(event) {
    if (mobile) {
        if (currentlyDragging == undefined && (event.target.tagName == "TD" || event.target.tagName == "TR")) {
            currentlyDragging = event.target;

            // add selected class

            if (currentlyDragging.tagName == "TD") {
                currentlyDragging = currentlyDragging.parentElement;
                if (currentlyDragging.tagName == "TH") {
                    return;
                }
            }

            currentlyDragging.classList.add("selected");
        }
        else if (currentlyDragging != undefined) {
            dragEnd(event, currentlyDragging);
            currentlyDragging.classList.remove("selected");
            currentlyDragging = undefined;
        }
    }
}

// before the page is loaded, sort the players table
function sortPlayers() {
    sortTable(document.getElementById("players-div").querySelector("table").querySelector("tbody"));
}

function formatTeamLists() {
    let team1 = "["
    let team2 = "["
    let team3 = "["
    let team4 = "["

    let team1Table = document.getElementById("team1-div").querySelector("table").querySelector("tbody");
    let team2Table = document.getElementById("team2-div").querySelector("table").querySelector("tbody");
    let team3Table = document.getElementById("team3-div").querySelector("table").querySelector("tbody");
    let team4Table = document.getElementById("team4-div").querySelector("table").querySelector("tbody");

    for (let i = 1; i < team1Table.children.length; i++) {
        if (i != 1) {
            team1 += ', ';
        }
        team1 += '"' + team1Table.children[i].children[0].innerHTML + '"';
    }
    for (let i = 1; i < team2Table.children.length; i++) {
        if (i != 1) {
            team2 += ', ';
        }
        team2 += '"' + team2Table.children[i].children[0].innerHTML + '"';
    }
    for (let i = 1; i < team3Table.children.length; i++) {
        if (i != 1) {
            team3 += ', ';
        }
        team3 += '"' + team3Table.children[i].children[0].innerHTML + '"';
    }
    for (let i = 1; i < team4Table.children.length; i++) {
        if (i != 1) {
            team4 += ', ';
        }
        team4 += '"' + team4Table.children[i].children[0].innerHTML + '"';
    }

    team1 += "]";
    team2 += "]";
    team3 += "]";
    team4 += "]";

    return [team1, team2, team3, team4];
}

function updateWinChances() {
    // get each team's player's codenames then use api to get their win chances

    let mode_index;

    if (currentMode == "sm5") {
        mode_index = 0;
    }
    else {
        mode_index = 1;
    }

    let playersTable = document.getElementById("players-div").querySelector("table").querySelector("tbody");

    for (let i = 1; i < playersTable.children.length; i++) {
        playersTable.children[i].children[1].innerHTML = Math.round(all_players[playersTable.children[i].children[0].innerHTML][mode_index] * 100) / 100;
    }

    teams = formatTeamLists();
    team1 = teams[0];
    team2 = teams[1];
    team3 = teams[2];
    team4 = teams[3];

    if (team1 == "[]" || team2 == "[]") {
        return;
    }

    if (numTeams > 2) {
        if (team3 == "[]" && team4 == "[]") {
            return;
        }
    }

    let xhr = new XMLHttpRequest();
    let url = "/api/internal/win_chances/" + currentMode;
    let params = "team1=" + team1 + "&team2=" + team2 + "&team3=" + team3 + "&team4=" + team4;
    xhr.open("GET", url + "?" + params, true);
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            let winChances = JSON.parse(xhr.responseText);
            
            // round
            let team1WinChance = Math.round(winChances[0] * 100 * 100) / 100;
            let team2WinChance = Math.round(winChances[1] * 100 * 100) / 100;
            let team3WinChance = Math.round(winChances[2] * 100 * 100) / 100;
            let team4WinChance = Math.round(winChances[3] * 100 * 100) / 100;

            document.getElementById("team1-div").querySelector("h2").innerHTML = "Team 1: " + team1WinChance + "%";
            document.getElementById("team2-div").querySelector("h2").innerHTML = "Team 2: " + team2WinChance + "%";
            document.getElementById("team3-div").querySelector("h2").innerHTML = "Team 3: " + team3WinChance + "%";
            document.getElementById("team4-div").querySelector("h2").innerHTML = "Team 4: " + team4WinChance + "%";

            // make sure ratings are up to date with the mode

            let team1Table = document.getElementById("team1-div").querySelector("table").querySelector("tbody");
            let team2Table = document.getElementById("team2-div").querySelector("table").querySelector("tbody");
            let team3Table = document.getElementById("team3-div").querySelector("table").querySelector("tbody");
            let team4Table = document.getElementById("team4-div").querySelector("table").querySelector("tbody");

            for (let i = 1; i < team1Table.children.length; i++) {
                team1Table.children[i].children[1].innerHTML = Math.round(all_players[team1Table.children[i].children[0].innerHTML][mode_index] * 100) / 100;
            }
            for (let i = 1; i < team2Table.children.length; i++) {
                team2Table.children[i].children[1].innerHTML = Math.round(all_players[team2Table.children[i].children[0].innerHTML][mode_index] * 100) / 100;
            }
            for (let i = 1; i < team3Table.children.length; i++) {
                team3Table.children[i].children[1].innerHTML = Math.round(all_players[team3Table.children[i].children[0].innerHTML][mode_index] * 100) / 100;
            }
            for (let i = 1; i < team4Table.children.length; i++) {
                team4Table.children[i].children[1].innerHTML = Math.round(all_players[team4Table.children[i].children[0].innerHTML][mode_index] * 100) / 100;
            }
        }
    }
    xhr.send(params);

}

function matchmakePlayers() {
    teams = formatTeamLists();
    team1 = teams[0];
    team2 = teams[1];
    team3 = teams[2];
    team4 = teams[3];

    // check for empty teams

    if (team1 == "[]" && team2 == "[]" && team3 == "[]" && team4 == "[]") {
        return;
    }

    let xhr = new XMLHttpRequest();
    let url = "/api/internal/matchmake/" + currentMode;
    let params = "team1=" + team1 + "&team2=" + team2 + "&team3=" + team3 + "&team4=" + team4 + "&num_teams=" + numTeams;
    xhr.open("GET", url + "?" + params, true);
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            let matchmadeTeams = JSON.parse(xhr.responseText);
            let team1Table = document.getElementById("team1-div").querySelector("table").querySelector("tbody");
            let team2Table = document.getElementById("team2-div").querySelector("table").querySelector("tbody");
            let team3Table = document.getElementById("team3-div").querySelector("table").querySelector("tbody");
            let team4Table = document.getElementById("team4-div").querySelector("table").querySelector("tbody");

            team1Table.innerHTML = "<tr><th>Player</th><th>Rating</th></tr>";
            team2Table.innerHTML = "<tr><th>Player</th><th>Rating</th></tr>";
            team3Table.innerHTML = "<tr><th>Player</th><th>Rating</th></tr>";
            team4Table.innerHTML = "<tr><th>Player</th><th>Rating</th></tr>";

            let mode_index;

            if (currentMode == "sm5") {
                mode_index = 0;
            }
            else {
                mode_index = 1;
            }

            for (let i = 0; i < matchmadeTeams[0].length; i++) {
                team1Table.innerHTML += "<tr draggable='true' ondragend='dragEnd(event)'><td>" + matchmadeTeams[0][i] + "</td><td>" + Math.round(all_players[matchmadeTeams[0][i]][mode_index] * 100) / 100 + "</td></tr>";
            }
            for (let i = 0; i < matchmadeTeams[1].length; i++) {
                team2Table.innerHTML += "<tr draggable='true' ondragend='dragEnd(event)'><td>" + matchmadeTeams[1][i] + "</td><td>" + Math.round(all_players[matchmadeTeams[1][i]][mode_index] * 100) / 100 + "</td></tr>";
            }
            for (let i = 0; i < matchmadeTeams[2].length; i++) {
                team3Table.innerHTML += "<tr draggable='true' ondragend='dragEnd(event)'><td>" + matchmadeTeams[2][i] + "</td><td>" + Math.round(all_players[matchmadeTeams[2][i]][mode_index] * 100) / 100 + "</td></tr>";
            }
            for (let i = 0; i < matchmadeTeams[3].length; i++) {
                team4Table.innerHTML += "<tr draggable='true' ondragend='dragEnd(event)'><td>" + matchmadeTeams[3][i] + "</td><td>" + Math.round(all_players[matchmadeTeams[3][i]][mode_index] * 100) / 100 + "</td></tr>";
            }

            updateWinChances();
        }
    }
    xhr.send(params);
}

function addUnratedPlayer() {
    let codename = "Unrated Player";
    let rating = 0;

    let team1Table = document.getElementById("team1-div").querySelector("table").querySelector("tbody");
    team1Table.innerHTML += "<tr draggable='true' ondragend='dragEnd(event)'><td>" + codename + "</td><td>" + rating + "</td></tr>";

    all_players[codename] = [0, 0];

    sortPlayers();
    updateWinChances();
}

function switchModeToSM5() {
    modeBtn = document.getElementById("modeBtn");
    currentMode = "sm5";
    modeBtn.innerHTML = "<h3>Switch Mode to Laserball</h3>";
    updateWinChances();
}

function switchModeToLaserball() {
    modeBtn = document.getElementById("modeBtn");
    currentMode = "laserball";
    modeBtn.innerHTML = "<h3>Switch Mode to SM5</h3>";
    updateWinChances();
}

function switchMode() {
    modeBtn = document.getElementById("modeBtn");
    if (currentMode == "sm5") {
        switchModeToLaserball();
    }
    else {
        switchModeToSM5();
    }
    updateWinChances();
}

// url args from game page when hitting rematchmake
function interpretUrlArgs() {
    if (team1 || team2) {
        let team1Table = document.getElementById("team1-div").querySelector("table").querySelector("tbody");
        let team2Table = document.getElementById("team2-div").querySelector("table").querySelector("tbody");

        team1Table.innerHTML = "<tr><th>Player</th><th>Rating</th></tr>";
        team2Table.innerHTML = "<tr><th>Player</th><th>Rating</th></tr>";

        let mode_index;

        if (currentMode == "sm5") {
            mode_index = 0;
        }
        else {
            mode_index = 1;
        }

        for (let i = 0; i < team1.length; i++) {
            team1Table.innerHTML += "<tr draggable='true' ondragend='dragEnd(event)'><td>" + team1[i] + "</td><td>" + Math.round(all_players[team1[i]][mode_index] * 100) / 100 + "</td></tr>";
        }
        for (let i = 0; i < team2.length; i++) {
            team2Table.innerHTML += "<tr draggable='true' ondragend='dragEnd(event)'><td>" + team2[i] + "</td><td>" + Math.round(all_players[team2[i]][mode_index] * 100) / 100 + "</td></tr>";
        }
    }
}

window.onload = function() {
    interpretUrlArgs();

    // default mode is sm5, if urlargs say it's laserball, switch to laserball
    console.log(currentMode);
    if (currentMode == "laserball") {
        console.log("switching to laserball");
        switchModeToLaserball();
    }

    sortPlayers();
    updateWinChances();

    // check if the user is on a mobile device (@media screen and (max-width: 991px) {)

    if (window.innerWidth <= 991) {
        mobile = true;
    }
}

window.onresize = function() {
    if (window.innerWidth <= 991) {
        mobile = true;
    }
    else {
        mobile = false;
    }
}

// onclick is used for mobile devices (anywhere)

document.onclick = onClick;