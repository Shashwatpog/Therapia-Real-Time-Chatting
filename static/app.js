document.addEventListener("DOMContentLoaded", () => {
    const chat = document.getElementById("chat-messages");
    const messageInput = document.getElementById("message-input");
    const sendButton = document.getElementById("send-button");
    const socket = io.connect("http://127.0.0.1:5000"); // Replace with your server URL

    socket.on("connect", () => {
        socket.emit("join", {}); // Join the chat room (if you have a room system)
    });

    socket.on("message", (data) => {
        const message = document.createElement("div");
        message.innerText = data.message;
        chat.appendChild(message);
        chat.scrollTop = chat.scrollHeight; // Scroll to the latest message
    });

    sendButton.addEventListener("click", () => {
        const messageText = messageInput.value.trim();
        console.log("Sending Message:", messageText);  // Add this line to log sent messages
        if (messageText) {
            socket.emit("message", { message: messageText });
            messageInput.value = "";
        }
    });

    messageInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            const messageText = messageInput.value.trim();
            if (messageText) {
                socket.emit("message", { message: messageText });
                messageInput.value = "";
            }
        }
    });
});
