
let conversationId = crypto.randomUUID();

async function sendMessage() {

    const input = document.getElementById("user-input");
    const chatBox = document.getElementById("chat-box");
    const sendButton = document.getElementById("send-btn");

    const message = input.value.trim();

    if (!message) return;

    // Display user message
    const userDiv = document.createElement("div");
    userDiv.className = "message user";
    userDiv.textContent = message;
    chatBox.appendChild(userDiv);

    input.value = "";

    // Show loading message
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "message bot";
    loadingDiv.textContent = "StudyBuddy is thinking...";
    chatBox.appendChild(loadingDiv);

    chatBox.scrollTop = chatBox.scrollHeight;
    sendButton.disabled = true;

    try {

        const response = await fetch("/chat", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: message,
                conversation_id: conversationId
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Request failed.");
        }

        loadingDiv.textContent = data.reply;

    } catch (error) {

        loadingDiv.textContent = "Error: " + error.message;

    } finally {

        sendButton.disabled = false;
        chatBox.scrollTop = chatBox.scrollHeight;
        input.focus();

    }
}


// Start a fresh conversation
function newConversation() {

    conversationId = crypto.randomUUID();

    document.getElementById("chat-box").innerHTML =
        '<div class="message bot">Hello! I am ready for a new conversation!</div>';

}
