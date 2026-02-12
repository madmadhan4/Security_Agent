let pollInterval;

// Tab Switching Logic
document.querySelectorAll('.tab-btn').forEach(button => {
    button.addEventListener('click', () => {
        // Remove active class from all buttons and content
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        // Add active class to clicked button
        button.classList.add('active');

        // Show corresponding content
        const tabId = button.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
    });
});

async function startSimulation() {
    const language = document.getElementById("languageSelect").value;
    const btn = document.getElementById("startBtn");

    btn.disabled = true;
    btn.innerText = "Simulating...";

    // Clear logs
    document.getElementById("logs").innerHTML = "";
    document.getElementById("timeline").innerHTML = "";

    try {
        const response = await fetch("/api/start-simulation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ language: language })
        });

        if (response.ok) {
            pollInterval = setInterval(fetchStatus, 1000);

            // Switch to Checks tab automatically to show progress
            document.querySelector('[data-tab="checks"]').click();
        } else {
            alert("Failed to start simulation");
            btn.disabled = false;
        }
    } catch (error) {
        console.error("Error:", error);
        btn.disabled = false;
    }
}

async function fetchStatus() {
    try {
        const response = await fetch("/api/status");
        const data = await response.json();

        updateUI(data);

        if (data.status === "COMPLETED" || data.status === "ERROR") {
            clearInterval(pollInterval);
            document.getElementById("startBtn").disabled = false;
            document.getElementById("startBtn").innerText = "Start Simulation";
        }
    } catch (error) {
        console.error("Error fetching status:", error);
    }
}

function updateUI(data) {
    if (!data) return;

    // Update PR Header
    if (data.pr_details && data.pr_details.title) {
        document.getElementById("prTitle").innerText = data.pr_details.title;
    }

    // Update Checks Console
    const logsContainer = document.getElementById("logs");
    if (data.logs && data.logs.length > 0) {
        logsContainer.innerHTML = data.logs.map(log => `<div>${log}</div>`).join("");
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    // Update Status Badge
    const stateBadge = document.getElementById("prState");

    // Update Agent Graph Animation
    updateGraph(data.current_step);

    if (data.status === "COMPLETED") {
        if (data.pr_details && data.logs.some(l => l.includes("merged"))) {
            stateBadge.innerText = "Merged";
            stateBadge.className = "state state-merged";
        } else {
            stateBadge.innerText = "Closed";
            stateBadge.className = "state state-closed";
        }
    } else {
        stateBadge.innerText = "Open";
        stateBadge.className = "state state-open";
    }

    // Update Files List & Diff View
    if (data.pr_details && data.pr_details.files) {
        renderFileList(data);
    }

    // Update File Count Badge
    if (data.pr_details && data.pr_details.files) {
        document.getElementById("filesCount").innerText = Object.keys(data.pr_details.files).length;
    }

    // Populate Timeline (Conversation)
    renderTimeline(data);
}

// Global state to track selected file
let selectedFile = null;
let lastData = null;

function renderFileList(data) {
    lastData = data;
    const fileListEl = document.getElementById("fileList");
    if (!fileListEl) return; // Guard if element missing

    const files = Object.keys(data.pr_details.files);

    // Check if re-render needed (simple length check or if empty)
    if (fileListEl.children.length === 0 || fileListEl.children.length !== files.length) {
        fileListEl.innerHTML = "";
        files.forEach((filename, index) => {
            const li = document.createElement("li");
            li.innerText = filename;
            li.onclick = () => selectFile(filename);

            // Auto-select first/vulnerable file if nothing selected
            if (!selectedFile && index === 0) selectFile(filename);

            fileListEl.appendChild(li);
        });
    }

    // Update active class
    Array.from(fileListEl.children).forEach(li => {
        if (li.innerText === selectedFile) li.classList.add("active");
        else li.classList.remove("active");
    });

    // Update content for selected file
    if (selectedFile) {
        document.getElementById("filenameDisplay").innerText = selectedFile;
        // Original Content
        document.getElementById("vulnerableCode").innerText = data.pr_details.files[selectedFile] || "";

        // Fixed Content
        if (data.fixed_code && data.fixed_code[selectedFile]) {
            document.getElementById("secureCode").innerText = data.fixed_code[selectedFile];
        } else if (data.status === "COMPLETED" && (!data.fixed_code || !data.fixed_code[selectedFile])) {
            document.getElementById("secureCode").innerText = "(No changes required)";
        } else {
            document.getElementById("secureCode").innerText = "(Pending fix...)";
        }
    }

    // Show tests (global for now)
    if (data.generated_tests && data.generated_tests.length > 0) {
        document.getElementById("testCode").innerText = data.generated_tests.join("\n\n");
    }
}

function selectFile(filename) {
    selectedFile = filename;
    if (lastData) renderFileList(lastData);
}

function updateGraph(step) {
    const graph = document.getElementById("agent-graph");
    if (!graph) return;

    // Reset animations
    graph.className = "agent-graph"; // remove anim-* classes

    // Reset active nodes
    document.querySelectorAll(".agent-node").forEach(n => n.classList.remove("active"));

    if (!step) return;

    if (step.includes("Hacking")) {
        graph.classList.add("anim-hacking");
        document.getElementById("agent-supervisor").classList.add("active");
        document.getElementById("agent-hacker").classList.add("active");
    } else if (step.includes("Fixing")) {
        graph.classList.add("anim-fixing");
        document.getElementById("agent-supervisor").classList.add("active");
        document.getElementById("agent-fixer").classList.add("active");
    } else if (step.includes("Merging")) {
        graph.classList.add("anim-merging");
        document.getElementById("agent-supervisor").classList.add("active");
        document.getElementById("agent-github").classList.add("active");
    } else if (step.includes("Creating")) {
        document.getElementById("agent-github").classList.add("active");
    }
}

function renderTimeline(data) {
    const timeline = document.getElementById("timeline");
    let html = "";

    // Initial System Message
    html += createTimelineItem("System", "Ready to start simulation.");

    // Hacker Finding
    if (data.vulnerabilities && data.vulnerabilities.length > 0) {
        html += createTimelineItem("hacker-agent", `Found vulnerabilities: <ul>${data.vulnerabilities.map(v => `<li>${v}</li>`).join("")}</ul>`);
    }

    // Fixer Action
    if (data.fixed_code && Object.keys(data.fixed_code).length > 0) {
        html += createTimelineItem("fixer-agent", "Applied security patches and updated the file.");
    }

    // Test Generation
    if (data.generated_tests && data.generated_tests.length > 0) {
        html += createTimelineItem("fixer-agent", "Added security unit tests to verify fixes.");
    }

    // Supervisor Merge
    if (data.status === "COMPLETED" && data.logs.some(l => l.includes("merged"))) {
        html += createTimelineItem("supervisor-agent", "Constraints satisfied. Merging PR.");
    }

    timeline.innerHTML = html;
}

function createTimelineItem(user, text) {
    return `
    <div class="timeline-item">
        <div class="timeline-avatar" style="background-color: ${stringToColor(user)}"></div>
        <div class="timeline-comment">
            <div class="comment-header">
                <strong>${user}</strong> commented
            </div>
            <div class="comment-body">
                ${text}
            </div>
        </div>
    </div>`;
}

function stringToColor(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    let color = '#';
    for (let i = 0; i < 3; i++) {
        let value = (hash >> (i * 8)) & 0xFF;
        color += ('00' + value.toString(16)).substr(-2);
    }
    return color;
}
