import js
import asyncio
import time
from helpers import request, RoleDefaults, CommanderDefaults, HeavyDefaults, ScoutDefaults, AmmoDefaults, MedicDefaults
import traceback
from pyodide.ffi import create_proxy
from threading import Event
from typing import Optional

restart_event = False
restart_event_received = False

fire_table = js.document.getElementById("fire_team")
earth_table = js.document.getElementById("earth_team")
event_box = js.document.getElementById("events")
speed_text = js.document.getElementById("speed")
play_button = js.document.getElementById("play")
restart_button = js.document.getElementById("restart")
started = False
play = False
start_time: float = 0.0
game: Optional[dict] = None

def play_pause(arg):
    global play, started, start_time
    play = not play
    if play:
        play_button.innerHTML = "Pause"
    else:
        play_button.innerHTML = "Play"

    if not started:
        started = True
        start_time = time.time()

async def restart(arg):
    global play, started, start_time, game, restart_event, restart_event_received

    restart_event = True
    while not restart_event_received:
        await asyncio.sleep(0.01)

    play = False
    started = False
    start_time = 0.0
    play_button.innerHTML = "Play"
    event_box.innerHTML = ""

    for player in game["entity_starts"]:
        if player["type"] != "player":
            continue

        defaults = get_defaults_from_role(player["role"])

        player["row"].getElementsByTagName("td")[2].getElementsByTagName("p")[0].innerHTML = 0
        player["row"].getElementsByTagName("td")[3].getElementsByTagName("p")[0].innerHTML = defaults.lives
        player["row"].getElementsByTagName("td")[4].getElementsByTagName("p")[0].innerHTML = defaults.shots
        player["row"].getElementsByTagName("td")[5].getElementsByTagName("p")[0].innerHTML = defaults.missiles
        player["row"].getElementsByTagName("td")[6].getElementsByTagName("p")[0].innerHTML = 0
        player["row"].getElementsByTagName("td")[7].getElementsByTagName("p")[0].innerHTML = "0.00%"
        player["lives"] = defaults.lives
        player["shots"] = defaults.shots
        player["missiles"] = defaults.missiles
        player["downed"] = False
        player["rapid_fire"] = False
        player["special_points"] = 0
        player["shots_hit"] = 0
        player["shots_fired"] = 0


    await play_events(game)

play_button.addEventListener("click", create_proxy(play_pause))
restart_button.addEventListener("click", create_proxy(restart))

def get_team_from_id(game, id):
    for team in game["teams"]:
        if team["index"] == id:
            return team
        
def get_entity_from_id(game, entity_id):
    for entity in game["entity_starts"]:
        if entity["entity_id"] == entity_id:
            return entity
        
def get_defaults_from_role(role) -> RoleDefaults:
    defaults: RoleDefaults = {
        1: CommanderDefaults,
        2: HeavyDefaults,
        3: ScoutDefaults,
        4: AmmoDefaults,
        5: MedicDefaults
    }.get(role)

    return defaults

async def setup_game(game):
    global play, start_time, restart_event, restart_event_received
    for player in game["entity_starts"]:
        if player["type"] != "player":
            continue

        team = get_team_from_id(game, player["team"])

        if team["color_name"] == "Fire":
            table = fire_table
        else: # earth
            table = earth_table

        role = player["role"]
        
        defaults = get_defaults_from_role(role)

        row = js.document.createElement("tr")

        row.innerHTML = f'''
            <td><img src="/assets/roles/{defaults.name}_white.png" alt="role image" width="30" height="30"></td>
            <td><p class="player_codename">{player["name"]}</p></td>
            <td><p class="player_score">0</p></td>
            <td><p class="player_lives">{defaults.lives}</p></td>
            <td><p class="player_shots">{defaults.shots}</p></td>
            <td><p class="player_missiles">{defaults.missiles}</p></td>
            <td><p class="player_special_points">0</p></td>
            <td><p class="player_accuracy">0.00%</p></td>
        '''

        table.appendChild(row)

        # stuff we're gonna use at runtime

        player["lives"] = defaults.lives
        player["shots"] = defaults.shots
        player["missiles"] = defaults.missiles
        player["downed"] = False
        player["special_points"] = 0
        player["shots_hit"] = 0
        player["shots_fired"] = 0
        player["score"] = 0
        player["rapid_fire"] = False
        player["row"] = row
        player["table"] = table

    # TODO: add downed attribute to player


async def play_events(game):
    global play, start_time, restart_event, restart_event_received
    # iterate through events at certain time, don't run the event unless it's time
    # event["time"] is in milliseconds

    for event in game["events"]:
        if restart_event:
            restart_event = False
            restart_event_received = True
            return

        while not play:
            if restart_event:
                restart_event = False
                restart_event_received = True
                return
            await asyncio.sleep(0.01)

        event["type"] = int(event["type"])

        # wait until it's time to run the event
        while int(time.time() - start_time)*float(speed_text.value) < event["time"] / 1000:
            await asyncio.sleep(0.01)
        
        updated_arguments = []
        for arg in event["arguments"]:
            if arg.startswith("#") or arg.startswith("@"):
                updated_arguments.append(get_entity_from_id(game, arg)["name"])
            else:
                updated_arguments.append(arg)

        old_scroll_top = event_box.scrollTop + event_box.clientHeight
        old_scroll_height = event_box.scrollHeight

        event_box.innerHTML += f'<p>{"".join(updated_arguments)}</p>'

        # only scroll if we're at the bottom
        if old_scroll_top >= old_scroll_height: 
            event_box.scrollTop = event_box.scrollHeight + 100

        match event["type"]:
            case 201: # miss
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["shots_fired"] += 1
                if shooter["role"] != 4: # not ammo
                    shooter["shots"] -= 1
            case 202: # miss base
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["shots_fired"] += 1
                if shooter["role"] != 4: # not ammo
                    shooter["shots"] -= 1
            case 203: # shot base
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["shots_fired"] += 1
                shooter["shots_hit"] += 1
                if shooter["role"] != 4: # not ammo
                    shooter["shots"] -= 1
            case 204: # destroy base
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["shots_fired"] += 1
                shooter["shots_hit"] += 1
                if shooter["role"] != 4: # not ammo
                    shooter["shots"] -= 1
                if shooter["role"] != 2: # not heavy
                    shooter["special_points"] += 5
                shooter["score"] += 1001
            case 205: # damaged opponent
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["shots_fired"] += 1
                shooter["shots_hit"] += 1
                if shooter["role"] != 4: # not ammo
                    shooter["shots"] -= 1
                if shooter["role"] != 2: # not heavy
                    shooter["special_points"] += 1
                shooter["score"] += 100

                victim = get_entity_from_id(game, event["arguments"][2])
                victim["score"] -= 20
            case 206: # downed opponent
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["shots_fired"] += 1
                shooter["shots_hit"] += 1
                if shooter["role"] != 4: # not ammo
                    shooter["shots"] -= 1
                if shooter["role"] != 2: # not heavy
                    shooter["special_points"] += 1
                shooter["score"] += 100

                victim = get_entity_from_id(game, event["arguments"][2])
                victim["score"] -= 20
                if victim["lives"] > 0:
                    victim["lives"] -= 1
            case 207: # damaged teammate
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["shots_fired"] += 1
                shooter["shots_hit"] += 1
                if shooter["role"] != 4: # not ammo
                    shooter["shots"] -= 1
                shooter["score"] -= 100

                victim = get_entity_from_id(game, event["arguments"][2])
                victim["score"] -= 20
            case 208: # downed teammate
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["shots_fired"] += 1
                shooter["shots_hit"] += 1
                if shooter["role"] != 4: # not ammo
                    shooter["shots"] -= 1
                shooter["score"] -= 100

                victim = get_entity_from_id(game, event["arguments"][2])
                victim["score"] -= 20
                if victim["lives"] > 0:
                    victim["lives"] -= 1
            case 303: # missile base
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["missiles"] -= 1
                if shooter["role"] != 2: # not heavy
                    shooter["special_points"] += 5
                shooter["score"] += 1001
            case 304: # missile missed
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["missiles"] -= 1
            case 306: # missile opponent
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["missiles"] -= 1
                if shooter["role"] != 2: # not heavy
                    shooter["special_points"] += 2
                shooter["score"] += 500

                victim = get_entity_from_id(game, event["arguments"][2])
                victim["score"] -= 100
                victim["lives"] -= 2
            case 308: # missile teammate
                shooter = get_entity_from_id(game, event["arguments"][0])
                shooter["missiles"] -= 1
                shooter["score"] -= 500

                victim = get_entity_from_id(game, event["arguments"][2])
                victim["score"] -= 100
                victim["lives"] -= 2
            case 400: # rapid fire
                player = get_entity_from_id(game, event["arguments"][0])
                player["special_points"] -= 15
                player["rapid_fire"] = True
            case 404: # activate nuke
                nuker = get_entity_from_id(game, event["arguments"][0])
                nuker["special_points"] -= 20
            case 405: # nuke opponent
                nuker = get_entity_from_id(game, event["arguments"][0])

                for player in game["entity_starts"]:
                    if player["team"] != nuker["team"] and player["type"] == "player":
                        if player["lives"] < 3:
                            player["lives"] = 0
                        else:
                            player["lives"] -= 3

                nuker["score"] += 500
            case 500: # resupply ammo
                resupplier = get_entity_from_id(game, event["arguments"][0])
                resupplyee = get_entity_from_id(game, event["arguments"][2])
                defaults = get_defaults_from_role(resupplyee["role"])

                resupplier["shots_fired"] += 1
                resupplier["shots_hit"] += 1

                resupplyee["shots"] += defaults.shots_resupply
                if resupplyee["shots"] > defaults.shots_max:
                    resupplyee["shots"] = defaults.shots_max
                
                resupplyee["rapid_fire"] = False
            case 502: # resupply lives
                resupplier = get_entity_from_id(game, event["arguments"][0])
                resupplyee = get_entity_from_id(game, event["arguments"][2])
                defaults = get_defaults_from_role(resupplyee["role"])

                resupplier["shots_fired"] += 1
                resupplier["shots_hit"] += 1

                resupplyee["lives"] += defaults.lives_resupply
                if resupplyee["lives"] > defaults.lives_max:
                    resupplyee["lives"] = defaults.lives_max

                resupplyee["rapid_fire"] = False
            case 510: # ammo boost
                booster = get_entity_from_id(game, event["arguments"][0])

                for player in game["entity_starts"]:
                    if player["team"] == booster["team"] and player["type"] == "player" and not player["downed"]:
                        defaults = get_defaults_from_role(player["role"])
                        player["shots"] += defaults.shots_resupply
                        if player["shots"] > defaults.shots_max:
                            player["shots"] = defaults.shots_max
            case 512: # lives boost
                booster = get_entity_from_id(game, event["arguments"][0])

                for player in game["entity_starts"]:
                    if player["team"] == booster["team"] and player["type"] == "player" and not player["downed"]:
                        defaults = get_defaults_from_role(player["role"])
                        player["lives"] += defaults.lives_resupply
                        if player["lives"] > defaults.lives_max:
                            player["lives"] = defaults.lives_max

            case 600: # penalty
                penaltyee = get_entity_from_id(game, event["arguments"][2])
                penaltyee["score"] -= 1000
                # down

        # update table
        for player in game["entity_starts"]:
            if player["type"] != "player":
                continue

            defaults = get_defaults_from_role(player["role"])

            # update
            if player["shots_fired"] == 0:
                accuracy = "0.00%"
            else:
                accuracy = str(round((player["shots_hit"] / player["shots_fired"])*100, 2)) + "%"

            player["row"].getElementsByTagName("td")[2].getElementsByTagName("p")[0].innerHTML = player["score"]
            player["row"].getElementsByTagName("td")[3].getElementsByTagName("p")[0].innerHTML = player["lives"]
            player["row"].getElementsByTagName("td")[4].getElementsByTagName("p")[0].innerHTML = player["shots"]
            player["row"].getElementsByTagName("td")[5].getElementsByTagName("p")[0].innerHTML = player["missiles"]
            player["row"].getElementsByTagName("td")[6].getElementsByTagName("p")[0].innerHTML = player["special_points"]
            player["row"].getElementsByTagName("td")[7].getElementsByTagName("p")[0].innerHTML = accuracy

            table = player["table"]
            
            switching = True
            while switching:
                switching = False
                rows = table.rows
                for i in range(1, rows.length - 1):
                    shouldSwitch = False
                    x = rows[i].getElementsByTagName("td")[2].getElementsByTagName("p")[0]
                    y = rows[i + 1].getElementsByTagName("td")[2].getElementsByTagName("p")[0]
                    if int(x.innerHTML) < int(y.innerHTML):
                        shouldSwitch = True
                        break
                if shouldSwitch:
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i])
                    switching = True

async def play_replay(game):
    await setup_game(game)
    await play_events(game)

async def main():
    global game
    print("Starting replay")
    resp = await request(f"/api/game/{js.game_id}")
    game = await resp.json()
    await play_replay(game)
    

async def error_wrap():
    try:
        await main()
    except Exception as e:
        traceback.print_exc()

asyncio.ensure_future(error_wrap())