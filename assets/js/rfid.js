
port = null;
mostRecentTag = null;
scanningHighFrequency = false;

function getCookie() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === ("csrftoken=")) {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}

function openPlayerPage(tag) {
    fetch(`/api/player/${tag}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
        },
        body: JSON.stringify({

        })
    })
    .then(response => {
        if (response.ok) {
            response.json().then(data => {
                window.location.href = `/player/${data.codename}`
            });
        }
        else if (response.status === 404) {
            // tag is not associated with a player
            alert("Tag not associated with a player. Please add the tag to a player first.");
        }
        else {
            console.error("Failed to open player page:", response.statusText);
            alert("Failed to open player page. Please try again.");
        }
    });
}

function handleSerialApi(value) {
    tag = Number(value);
    
    if (!isNaN(tag) && tag > 10) {
        mostRecentTag = tag;

        // check if admin in url
        if (window.location.pathname.includes("/admin/")) {
            // don't open player page, just add tag
            return true;
        }

        fetch(`/api/player/${tag}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken")
            },
            body: JSON.stringify({

            })
        })
        .then(response => {
            if (response.ok) {
                response.json().then(data => {
                    window.location.href = `/player/${data.codename}`
                });
            }
        });
        return true;
    }
    return false;
}

async function openPort() {
    const ports = await navigator.serial.getPorts();

    if (ports.length > 0) {
        // use the first port
        port = ports[0];
    }
    else {
        // select the serial port because we haven't gotten permission yet
        port = await navigator.serial.requestPort();
    }

    // open it
    await port.open({ baudRate: 9600 });
}

async function readPortData() {
    // print the decoded data
    const decoder = new TextDecoderStream();
    const inputDone = port.readable.pipeTo(decoder.writable);
    const inputStream = decoder.readable;
    const reader = inputStream.getReader();

    if (document.getElementById("rfid_button")) {
        document.getElementById("rfid_button").style.display = "none";
    }

    while (true) {
        const { value, done } = await reader.read();
        if (done) {
            break;
        }
        result = handleSerialApi(value);
        if (result) {
            // if we handled the value, break out of the loop
            break;
        }
    }

    reader.releaseLock();
    await inputDone;

    // show rfid button

    if (document.getElementById("rfid_button")) {
        document.getElementById("rfid_button").style.display = "block";
    }
}

async function scanLowFrequencyRfid() {
    if (!port || !port.readable) {
        await openPort();
        await readPortData();
    }
}

async function checkPermission() {
    const ports = await navigator.serial.getPorts();
    if (ports.length > 0) {
        if (!port || !port.readable) {
            // we have permission
            scanLowFrequencyRfid();
            return;
        }
    }
}

async function checkSupport() {
    if (!("serial" in navigator) && !("NDEFReader" in window)) {
        console.log("Neither Web Serial API nor Web NFC API is supported in this browser.");
        // hide the rfid button
        if (document.getElementById("rfid_button")) {
            document.getElementById("rfid_button").style.display = "none";
        }
        return;
    }

    if ("serial" in navigator) {
        // check if we already have permission
        setInterval(checkPermission, 2000);
        checkPermission();
    }
}

async function addLowFrequencyTag(player_id) {
    async function waitForTag() {
        if (!port) {
            await openPort();
            setTimeout(readPortData, 0);
        }

        if (mostRecentTag == null) {
            // loop until a tag is scanned
            setTimeout(waitForTag, 1000, true);
        }
        else {
            fetch(`/admin/player/${player_id}/add_tag`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    "tag": mostRecentTag,
                }),
            }).then(response => {
                if (response.ok) {
                    location.reload();
                }
                else {
                    alert("Failed to add tag");
                }
            });
        }
    }
    await waitForTag();
}

function scanHighFrequencyTag() {
    // web nfc api

    if ("NDEFReader" in window) {
        const ndef = new NDEFReader();
        return new Promise((resolve, reject) => {
            ndef.scan().then(() => {
                ndef.onreading = event => {
                    resolve(event.serialNumber); // resolve the promise with the serial number
                };
                ndef.onreadingerror = error => {
                    reject(error); // reject the promise on error
                };
            }).catch(error => {
                reject(error); // reject the promise if scan fails
            });
        });
    }
    else {
        return Promise.reject("Web NFC not supported."); // reject if NFC is not supported
    }
}

async function addHighFrequencyTag(player_id) {
    const tag = await scanHighFrequencyTag().catch(error => {
        console.error("Failed to scan tag:", error);
        alert("Failed to scan tag. Please try again.");
        return null; // Return null if scanning fails
    });

    if (tag == null) {
        return;
    }
    
    fetch(`/admin/player/${player_id}/add_tag`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            "tag": tag,
            "type": "HF" // high frequency rfid
        }),
    }).then(response => {
        if (response.ok) {
            location.reload();
        }
        else {
            console.error("Failed to add tag:", response.statusText);
            alert("Failed to add tag");
        }
    });
}

async function scanHighFrequencyRfid() {
    if (!("NDEFReader" in window) || scanningHighFrequency) {
        return;
    }

    scanningHighFrequency = true;

    await scanHighFrequencyTag().then(tag => {
        if (tag) {
            openPlayerPage(tag);
        } else {
            console.error("No tag scanned or scanning failed.");
        }
    }).catch(error => {
        console.error("Error reading high frequency RFID:", error);
        alert("Failed to read high frequency RFID. Please try again.");
    });
}

function addTag(player_id) {
    // check which type of rfid is being used

    if ("NDEFReader" in window) {
        // high frequency rfid
        addHighFrequencyTag(player_id);
    }
    else if ("serial" in navigator) {
        // low frequency rfid
        addLowFrequencyTag(player_id);
    }
    else {
        alert("No RFID reader available.");
    }
}

async function rfidButton() {
    // check which type of rfid is being used
    if ("NDEFReader" in window) {
        await scanHighFrequencyRfid();
    }
    else if ("serial" in navigator) {
        await scanLowFrequencyRfid();
    }
    else {
        alert("No RFID reader available.");
    }
}

document.addEventListener("DOMContentLoaded", checkSupport);