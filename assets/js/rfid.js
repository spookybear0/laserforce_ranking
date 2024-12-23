
port = null;
mostRecentTag = null;
openPlayerPage = false;

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

function handleSerialApi(value) {
    tag = Number(value);
    
    if (!isNaN(tag) && tag > 10) {
        console.log(tag);
        mostRecentTag = tag;

        if (openPlayerPage) {
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
                        console.log(data);
                        window.location.href = `/player/${data.codename}`
                    });
                }
            });
        }
    }
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

    document.getElementById("rfid_button").style.display = "none";

    while (true) {
        const { value, done } = await reader.read();
        if (done) {
            break;
        }
        handleSerialApi(value);
    }

    reader.releaseLock();
    await inputDone;

    // show rfid button

    document.getElementById("rfid_button").style.display = "block";
}

async function readRfid() {
    openPlayerPage = true;
    if (!port || !port.readable) {
        await openPort();
        await readPortData();
    }
}

async function checkPermission() {
    const ports = await navigator.serial.getPorts();
    if (ports.length > 0) {
        if (!port || !port.readable) {
            console.log("Already have permission, connecting to port");
            // we have permission
            readRfid();
            return;
        }
    }
}

async function checkSupport() {
    if (!("serial" in navigator)) {
        console.log("Web serial not supported.");
        // hide the rfid button
        document.getElementById("rfid_button").style.display = "none";
        return;
    }

    // check if we already have permission
    setInterval(checkPermission, 2000);
    checkPermission();
}

if (document.getElementById("rfid_button") != null) {
    document.addEventListener("DOMContentLoaded", checkSupport);
}