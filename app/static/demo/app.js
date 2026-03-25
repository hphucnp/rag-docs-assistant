const bundleForm = document.getElementById("bundle-form");
const uploadButton = document.getElementById("upload-button");
const uploadStatus = document.getElementById("upload-status");
const cvIdInput = document.getElementById("cv-id");
const jdIdInput = document.getElementById("jd-id");
const notesIdInput = document.getElementById("notes-id");
const currentSummaryInput = document.getElementById("current-summary");

const outputs = {
  "missing-skills": document.getElementById("missing-skills-output"),
  "rewrite-summary": document.getElementById("rewrite-summary-output"),
  "highlight-achievements": document.getElementById("highlight-achievements-output"),
};

const actionLabels = {
  "missing-skills": "Analyzing missing skills...",
  "rewrite-summary": "Rewriting summary...",
  "highlight-achievements": "Finding achievements to highlight...",
};

function setUploadStatus(message, variant = "muted") {
  uploadStatus.textContent = message;
  uploadStatus.className = `status-box ${variant}`;
}

function ensureDocumentIds() {
  if (!cvIdInput.value.trim() || !jdIdInput.value.trim()) {
    throw new Error("Upload a bundle first or paste both CV ID and JD ID.");
  }
}

async function parseError(response) {
  try {
    const data = await response.json();
    return data.detail || JSON.stringify(data, null, 2);
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}

bundleForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(bundleForm);
  uploadButton.disabled = true;
  setUploadStatus("Uploading CV, JD, and notes...", "muted");

  try {
    const response = await fetch("/api/v1/match/upload-bundle", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    const payload = await response.json();
    cvIdInput.value = payload.cv_id || "";
    jdIdInput.value = payload.jd_id || "";
    notesIdInput.value = payload.notes_id || "";

    setUploadStatus(
      [
        "Bundle uploaded successfully.",
        `CV ID: ${payload.cv_id}`,
        `JD ID: ${payload.jd_id}`,
        `Notes ID: ${payload.notes_id || "none"}`,
      ].join("\n"),
      "success",
    );
  } catch (error) {
    setUploadStatus(`Upload failed: ${error.message}`, "error");
  } finally {
    uploadButton.disabled = false;
  }
});

async function runAction(action, button) {
  try {
    ensureDocumentIds();
  } catch (error) {
    outputs[action].textContent = error.message;
    return;
  }

  const params = new URLSearchParams({
    cv_id: cvIdInput.value.trim(),
    jd_id: jdIdInput.value.trim(),
  });

  if (notesIdInput.value.trim()) {
    params.set("notes_id", notesIdInput.value.trim());
  }

  if (action === "rewrite-summary" && currentSummaryInput.value.trim()) {
    params.set("current_summary", currentSummaryInput.value.trim());
  }

  button.disabled = true;
  outputs[action].textContent = actionLabels[action];

  try {
    const response = await fetch(`/api/v1/match/${action}?${params.toString()}`, {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    const payload = await response.json();

    if (action === "missing-skills") {
      outputs[action].textContent = payload.missing_skills || "No result.";
    } else if (action === "rewrite-summary") {
      outputs[action].textContent = payload.new_summary || "No result.";
    } else {
      outputs[action].textContent = payload.achievements_to_highlight || "No result.";
    }
  } catch (error) {
    outputs[action].textContent = `Request failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => runAction(button.dataset.action, button));
});
