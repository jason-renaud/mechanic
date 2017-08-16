$(document).ready(function() {

    var onMessage = function (data) {
        console.log(data)
        $("#mechanic-container").append("<p>Received: " + JSON.stringify(data) + "</p>");
    };
    var connectToServer = function () {
        var socket = io.connect("YOUR_APP_URL_HERE");
        socket.emit("client-connect", {data: "connection established"})
        socket.on("YOUR_ROUTING_KEY_HERE", onMessage);
    };
    connectToServer();
});
