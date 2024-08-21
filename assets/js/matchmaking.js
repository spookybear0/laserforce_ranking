
const roleImgs = ["assets/sm5/roles/commander.png", "assets/sm5/roles/heavy.png", "assets/sm5/roles/scout.png", "assets/sm5/roles/ammo.png", "assets/sm5/roles/medic.png"];

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
        team1 += '"' + team1Table.children[i].children[1].innerHTML + '"';
    }
    for (let i = 1; i < team2Table.children.length; i++) {
        if (i != 1) {
            team2 += ', ';
        }
        team2 += '"' + team2Table.children[i].children[1].innerHTML + '"';
    }
    for (let i = 1; i < team3Table.children.length; i++) {
        if (i != 1) {
            team3 += ', ';
        }
        team3 += '"' + team3Table.children[i].children[1].innerHTML + '"';
    }
    for (let i = 1; i < team4Table.children.length; i++) {
        if (i != 1) {
            team4 += ', ';
        }
        team4 += '"' + team4Table.children[i].children[1].innerHTML + '"';
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
        try {
            playersTable.children[i].children[1].innerHTML = Math.round(all_players[playersTable.children[i].children[0].innerHTML][mode_index] * 100) / 100;
        }
        catch (e) {}
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

            // check number of teams

            if (numTeams == 2) {
                let team1WinChance = Math.round(winChances[0][0] * 100 * 100) / 100;
                let team2WinChance = Math.round(winChances[0][1] * 100 * 100) / 100;

                document.getElementById("team1-div").querySelector("h2").innerHTML = "Team 1: " + team1WinChance + "%";
                document.getElementById("team2-div").querySelector("h2").innerHTML = "Team 2: " + team2WinChance + "%";
            }

            if (numTeams == 3) {
                let team1VsTeam2WinChance = Math.round(winChances[0][0] * 100 * 100) / 100;
                let team2VsTeam1WinChance = Math.round(winChances[0][1] * 100 * 100) / 100;
                let team1VsTeam3WinChance = Math.round(winChances[1][0] * 100 * 100) / 100;
                let team3VsTeam1WinChance = Math.round(winChances[1][1] * 100 * 100) / 100;
                let team2VsTeam3WinChance = Math.round(winChances[2][0] * 100 * 100) / 100;
                let team3VsTeam2WinChance = Math.round(winChances[2][1] * 100 * 100) / 100;

                document.getElementById("team1-div").querySelector("h2").innerHTML = "Team 1<br>vs Team 2: " + team1VsTeam2WinChance + "%<br>vs Team 3: " + team1VsTeam3WinChance + "%";
                document.getElementById("team2-div").querySelector("h2").innerHTML = "Team 2<br>vs Team 1: " + team2VsTeam1WinChance + "%<br>vs Team 3: " + team2VsTeam3WinChance + "%";
                document.getElementById("team3-div").querySelector("h2").innerHTML = "Team 3<br>vs Team 1: " + team3VsTeam1WinChance + "%<br>vs Team 2: " + team3VsTeam2WinChance + "%";
            }
            
            if (numTeams == 4) {
                let team1VsTeam2WinChance = Math.round(winChances[0][0] * 100 * 100) / 100;
                let team2VsTeam1WinChance = Math.round(winChances[0][1] * 100 * 100) / 100;
                let team1VsTeam3WinChance = Math.round(winChances[1][0] * 100 * 100) / 100;
                let team3VsTeam1WinChance = Math.round(winChances[1][1] * 100 * 100) / 100;
                let team1VsTeam4WinChance = Math.round(winChances[2][0] * 100 * 100) / 100;
                let team4VsTeam1WinChance = Math.round(winChances[2][1] * 100 * 100) / 100;
                let team2VsTeam3WinChance = Math.round(winChances[3][0] * 100 * 100) / 100;
                let team3VsTeam2WinChance = Math.round(winChances[3][1] * 100 * 100) / 100;
                let team2VsTeam4WinChance = Math.round(winChances[4][0] * 100 * 100) / 100;
                let team4VsTeam2WinChance = Math.round(winChances[4][1] * 100 * 100) / 100;
                let team3VsTeam4WinChance = Math.round(winChances[5][0] * 100 * 100) / 100;
                let team4VsTeam3WinChance = Math.round(winChances[5][1] * 100 * 100) / 100;

                document.getElementById("team1-div").querySelector("h2").innerHTML = "Team 1<br>vs Team 2: " + team1VsTeam2WinChance + "%<br>vs Team 3: " + team1VsTeam3WinChance + "%<br>vs Team 4: " + team1VsTeam4WinChance + "%";
                document.getElementById("team2-div").querySelector("h2").innerHTML = "Team 2<br>vs Team 1: " + team2VsTeam1WinChance + "%<br>vs Team 3: " + team2VsTeam3WinChance + "%<br>vs Team 4: " + team2VsTeam4WinChance + "%";
                document.getElementById("team3-div").querySelector("h2").innerHTML = "Team 3<br>vs Team 1: " + team3VsTeam1WinChance + "%<br>vs Team 2: " + team3VsTeam2WinChance + "%<br>vs Team 4: " + team3VsTeam4WinChance + "%";
                document.getElementById("team4-div").querySelector("h2").innerHTML = "Team 4<br>vs Team 1: " + team4VsTeam1WinChance + "%<br>vs Team 2: " + team4VsTeam2WinChance + "%<br>vs Team 3: " + team4VsTeam3WinChance + "%";
            }


            // make sure ratings are up to date with the mode

            let team1Table = document.getElementById("team1-div").querySelector("table").querySelector("tbody");
            let team2Table = document.getElementById("team2-div").querySelector("table").querySelector("tbody");
            let team3Table = document.getElementById("team3-div").querySelector("table").querySelector("tbody");
            let team4Table = document.getElementById("team4-div").querySelector("table").querySelector("tbody");

            
            for (let i = 1; i < team1Table.children.length; i++) {
                try {
                    team1Table.children[i].children[2].innerHTML = Math.round(all_players[team1Table.children[i].children[1].innerHTML][mode_index] * 100) / 100;
                }
                catch (e) {}
            }
            for (let i = 1; i < team2Table.children.length; i++) {
                try {
                    team2Table.children[i].children[2].innerHTML = Math.round(all_players[team2Table.children[i].children[1].innerHTML][mode_index] * 100) / 100;
                }
                catch (e) {}
            }
            for (let i = 1; i < team3Table.children.length; i++) {
                try {
                    team3Table.children[i].children[2].innerHTML = Math.round(all_players[team3Table.children[i].children[1].innerHTML][mode_index] * 100) / 100;
                }
                catch (e) {}
            }
            for (let i = 1; i < team4Table.children.length; i++) {
                try {
                    team4Table.children[i].children[2].innerHTML = Math.round(all_players[team4Table.children[i].children[1].innerHTML][mode_index] * 100) / 100;
                }
                catch (e) {}
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
    let params = "team1=" + team1 + "&team2=" + team2 + "&team3=" + team3 + "&team4=" + team4 + "&num_teams=" + numTeams + "&matchmake_roles=" + matchmakeRoles;
    xhr.open("GET", url + "?" + params, true);
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            let jsonData = JSON.parse(xhr.responseText);

            let matchmadeTeams = jsonData["teams"];
            let matchmadeRoles = jsonData["roles"];

            let className = "role-cell-hidden";
            if (matchmakeRoles) {
                className = "role-cell";
            }

            let team1Table = document.getElementById("team1-div").querySelector("table").querySelector("tbody");
            let team2Table = document.getElementById("team2-div").querySelector("table").querySelector("tbody");
            let team3Table = document.getElementById("team3-div").querySelector("table").querySelector("tbody");
            let team4Table = document.getElementById("team4-div").querySelector("table").querySelector("tbody");

            team1Table.innerHTML = `<tr><th class="${className}"></th><th>Player</th><th>Rating</th></tr>`;
            team2Table.innerHTML = `<tr><th class="${className}"></th><th>Player</th><th>Rating</th></tr>`;
            team3Table.innerHTML = `<tr><th class="${className}"></th><th>Player</th><th>Rating</th></tr>`;
            team4Table.innerHTML = `<tr><th class="${className}"></th><th>Player</th><th>Rating</th></tr>`;

            let mode_index;

            if (currentMode == "sm5") {
                mode_index = 0;
            }
            else {
                mode_index = 1;
            }

            // this could easily be a for loop, but I'm too lazy to change it

            let i = 0;
            for (var key in matchmadeTeams[0]) {
                roleImg = "";
                if (matchmakeRoles) {
                    roleImg = `<img src="${roleImgs[matchmadeRoles[0][i]-1]}" width="25" height="25">`;
                }
                team1Table.innerHTML += `<tr draggable='true' ondragend='dragEnd(event)'><td class="${className}">${roleImg}</td><td>${key}</td><td>${Math.round(matchmadeTeams[0][key][mode_index] * 100) / 100}</td></tr>`;
                i++;
            }
            i = 0;
            for (var key in matchmadeTeams[1]) {
                roleImg = "";
                if (matchmakeRoles) {
                    roleImg = `<img src="${roleImgs[matchmadeRoles[1][i]-1]}" width="25" height="25">`
                }
                team2Table.innerHTML += `<tr draggable='true' ondragend='dragEnd(event)'><td class="${className}">${roleImg}</td><td>${key}</td><td>${Math.round(matchmadeTeams[1][key][mode_index] * 100) / 100}</td></tr>`;
                i++
            }
            i = 0;
            for (var key in matchmadeTeams[2]) {
                roleImg = "";
                if (matchmakeRoles) {
                    roleImg = `<img src="${roleImgs[matchmadeRoles[2][i]-1]}" width="25" height="25">`
                }
                team3Table.innerHTML += `<tr draggable='true' ondragend='dragEnd(event)'><td class="${className}">${roleImg}</td><td>${key}</td><td>${Math.round(matchmadeTeams[2][key][mode_index] * 100) / 100}</td></tr>`;
                i++
            }
            i = 0;
            for (var key in matchmadeTeams[3]) {
                roleImg = "";
                if (matchmakeRoles) {
                    roleImg = `<img src="${roleImgs[matchmadeRoles[3][i]-1]}" width="25" height="25">`
                }
                team4Table.innerHTML += `<tr draggable='true' ondragend='dragEnd(event)'><td class="${className}">${roleImg}</td><td>${key}</td><td>${Math.round(matchmadeTeams[3][key][mode_index] * 100) / 100}</td></tr>`;
                i++
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
    team1Table.innerHTML += "<tr draggable='true' ondragend='dragEnd(event)'><td class=\"role-cell-hidden\"></td><td>" + codename + "</td><td>" + rating + "</td></tr>";

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

function switchMatchmakingRoles() {
    var newClass = "role-cell-hidden";

    if (matchmakeRoles) {
        matchmakeRoles = false;
        document.getElementById("matchmakeRolesBtn").innerHTML = "<h3>Matchmake Roles/Players</h3>";
    }
    else {
        matchmakeRoles = true;
        document.getElementById("matchmakeRolesBtn").innerHTML = "<h3>Matchmake Players Only</h3>";
        newClass = "role-cell";
    }

    // show/hide role cells

    let playersTable = document.getElementById("players-div").querySelector("table").querySelector("tbody");

    for (let i = 0; i < playersTable.children.length; i++) {
        playersTable.children[i].children[0].className = newClass;
    }

    let team1Table = document.getElementById("team1-div").querySelector("table").querySelector("tbody");
    let team2Table = document.getElementById("team2-div").querySelector("table").querySelector("tbody");
    let team3Table = document.getElementById("team3-div").querySelector("table").querySelector("tbody");
    let team4Table = document.getElementById("team4-div").querySelector("table").querySelector("tbody");

    for (let i = 0; i < team1Table.children.length; i++) {
        team1Table.children[i].children[0].className = newClass;
    }
    for (let i = 0; i < team2Table.children.length; i++) {
        team2Table.children[i].children[0].className = newClass;
    }
    for (let i = 0; i < team3Table.children.length; i++) {
        team3Table.children[i].children[0].className = newClass;
    }
    for (let i = 0; i < team4Table.children.length; i++) {
        team4Table.children[i].children[0].className = newClass;
    }

    updateWinChances();
}

// url args from game page when hitting rematchmake
function interpretUrlArgs() {
    if (team1 || team2) {
        let team1Table = document.getElementById("team1-div").querySelector("table").querySelector("tbody");
        let team2Table = document.getElementById("team2-div").querySelector("table").querySelector("tbody");

        team1Table.innerHTML = "<tr><th class=\"role-cell-hidden\"></th><th>Player</th><th>Rating</th></tr>";
        team2Table.innerHTML = "<tr><th class=\"role-cell-hidden\"></th><th>Player</th><th>Rating</th></tr>";

        let mode_index;

        if (currentMode == "sm5") {
            mode_index = 0;
        }
        else {
            mode_index = 1;
        }

        for (let i = 0; i < team1.length; i++) {
            let player = team1[i];
            team1Table.innerHTML += "<tr draggable='true' ondragend='dragEnd(event)'><td class=\"role-cell-hidden\"></td><td>" + player[0] + "</td><td>" + Math.round(player[mode_index+1] * 100) / 100 + "</td></tr>";
        }
        for (let i = 0; i < team2.length; i++) {
            let player = team2[i];
            team2Table.innerHTML += "<tr draggable='true' ondragend='dragEnd(event)'><td class=\"role-cell-hidden\"></td><td>" + player[0] + "</td><td>" + Math.round(player[mode_index+1] * 100) / 100 + "</td></tr>";
        }
    }
}

window.onload = function() {
    interpretUrlArgs();

    // default mode is sm5, if urlargs say it's laserball, switch to laserball
    if (currentMode == "laserball") {
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