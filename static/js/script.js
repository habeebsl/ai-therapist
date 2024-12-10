document.addEventListener("DOMContentLoaded", () => {
    const sendButton = document.getElementById("send-btn")
    const messageInput = document.getElementById("message-input")
    const messagesArea = document.getElementById("messages-area")
    const rectangle = document.getElementById("rectangle")
    const box = document.getElementById("box")

    sendButton.addEventListener("click", sendMessage)

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage()
        }
    })

    rectangle.addEventListener("click", () => {
        get_notes()
        toggleBoxVisibility();
    })

    // Helper function: Toggle notes container visibility
    function toggleBoxVisibility() {
        if (box.style.display === "none" || box.style.display === "") {
            box.style.display = "block";
        } else {
            box.style.display = "none";
        }
    }

    // Helper function: Create message elements
    function createMessageElement(role, message) {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('message-wrapper');
        const bubbleElement = document.createElement('div');
        bubbleElement.classList.add('chat-bubble', `${role}-bubble`);
        bubbleElement.textContent = message;
        messageWrapper.appendChild(bubbleElement);
        return messageWrapper;
    }

    // Get therapy notes and homework
    async function get_notes() {
        try {
            const response = await fetch("/get_notes", {
                method: "GET",
                headers: { "Content-Type": "application/json" }
            })

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json()
            console.log(data.therapy_notes)
            box.innerHTML = "";
            displayNotesAndHomework(data);

        } catch (error) {
            console.error("Error fetching notes:", error);
            box.textContent = "An error occurred while fetching the notes.";
        }
    }

    // Helper function: Display notes and homework
    function displayNotesAndHomework(data) {
        if (data.therapy_notes) {
            let note_header = document.createElement("h3")
            note_header.textContent = "Therapy Notes"
            note_header.style.textAlign = "center";
            note_header.style.padding = "5px"
            box.append(note_header)
            let notes = document.createElement("p");
            notes.textContent = data.therapy_notes;
            notes.style.padding = "10px";
            notes.style.paddingTop = "0";
            box.appendChild(notes);
        }

        if (data.homework) {
            let homework_header = document.createElement("h3")
            homework_header.textContent = "Homework"
            homework_header.style.textAlign = "center";
            homework_header.style.padding = "5px";
            box.append(homework_header)
            let homework = document.createElement("ul")
            homework.style.padding = "18px";
            homework.style.paddingTop = "0";
            for (let i in data.homework) {
                let nums = document.createElement("li")
                nums.textContent = data.homework[i]
                homework.appendChild(nums)
            }
            box.appendChild(homework)
        }

        if (!data.therapy_notes && (!data.homework || data.homework.length === 0)) {
            box.textContent = "Nothing to see here";
        }
    }

    // Send user message to server
    async function sendMessage() {
        let message = messageInput.value.trim()

        if (!message) return;

        messagesArea.appendChild(
            createMessageElement("user", message)
        )

        try {
            const response = await fetch("/send_message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message })
            })

            const data = await response.json()
            if (data.feedback === "inprogress") {
                messagesArea.appendChild(
                    createMessageElement("bot", data.message)
                )
                messageInput.value = ""
            }

            messagesArea.scrollTop = messagesArea.scrollHeight;

        } catch (error) {
            console.error("Error: ", error)
        }
    }
})
