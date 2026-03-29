import { reactive, ref } from "vue";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

const bundle = reactive({
  cvFile: null,
  jdFile: null,
  cvTitle: "Candidate Resume",
  jdTitle: "Target Job Description",
  notes: "",
});

const ids = reactive({
  cvId: "",
  jdId: "",
  notesId: "",
});

const currentSummary = ref("");

const uploadState = reactive({
  loading: false,
  variant: "muted",
  message: "No files uploaded yet.",
});

const outputs = reactive({
  "missing-skills": "Run the analysis to see missing skills.",
  "rewrite-summary": "Run the analysis to rewrite the summary.",
  "highlight-achievements": "Run the analysis to see recommended achievements.",
});

const loadingActions = reactive({
  "missing-skills": false,
  "rewrite-summary": false,
  "highlight-achievements": false,
});

const actionCards = [
  {
    key: "missing-skills",
    title: "Missing Skills",
    subtitle: "/missing-skills",
    button: "What skills are missing?",
    loading: "Analyzing missing skills...",
  },
  {
    key: "rewrite-summary",
    title: "Rewritten Summary",
    subtitle: "/rewrite-summary",
    button: "Rewrite summary for this job",
    loading: "Rewriting summary...",
  },
  {
    key: "highlight-achievements",
    title: "Achievements to Highlight",
    subtitle: "/highlight-achievements",
    button: "Which achievements should I highlight?",
    loading: "Finding achievements to highlight...",
  },
];

function setFile(event, key) {
  bundle[key] = event.target.files?.[0] || null;
}

function setUploadStatus(message, variant = "muted") {
  uploadState.message = message;
  uploadState.variant = variant;
}

function buildUrl(path, params) {
  const query = params ? `?${params.toString()}` : "";
  return `${apiBaseUrl}${path}${query}`;
}

async function parseError(response) {
  try {
    const data = await response.json();
    return data.detail || JSON.stringify(data, null, 2);
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}

function ensureDocumentIds() {
  if (!ids.cvId.trim() || !ids.jdId.trim()) {
    throw new Error("Upload a bundle first or paste both CV ID and JD ID.");
  }
}

async function uploadBundle() {
  if (!bundle.cvFile || !bundle.jdFile) {
    setUploadStatus("Please select both CV and JD files.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("cv_file", bundle.cvFile);
  formData.append("jd_file", bundle.jdFile);
  formData.append("cv_title", bundle.cvTitle);
  formData.append("jd_title", bundle.jdTitle);
  formData.append("notes", bundle.notes);

  uploadState.loading = true;
  setUploadStatus("Uploading CV, JD, and notes...", "muted");

  try {
    const response = await fetch(buildUrl("/api/v1/match/upload-bundle"), {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    const payload = await response.json();
    ids.cvId = payload.cv_id || "";
    ids.jdId = payload.jd_id || "";
    ids.notesId = payload.notes_id || "";

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
    uploadState.loading = false;
  }
}

async function runAction(action) {
  try {
    ensureDocumentIds();
  } catch (error) {
    outputs[action] = error.message;
    return;
  }

  const card = actionCards.find((item) => item.key === action);
  const params = new URLSearchParams({
    cv_id: ids.cvId.trim(),
    jd_id: ids.jdId.trim(),
  });

  if (ids.notesId.trim()) {
    params.set("notes_id", ids.notesId.trim());
  }

  if (action === "rewrite-summary" && currentSummary.value.trim()) {
    params.set("current_summary", currentSummary.value.trim());
  }

  loadingActions[action] = true;
  outputs[action] = card?.loading || "Running...";

  try {
    const response = await fetch(buildUrl(`/api/v1/match/${action}`, params), {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    const payload = await response.json();

    if (action === "missing-skills") {
      outputs[action] = payload.missing_skills || "No result.";
    } else if (action === "rewrite-summary") {
      outputs[action] = payload.new_summary || "No result.";
    } else {
      outputs[action] = payload.achievements_to_highlight || "No result.";
    }
  } catch (error) {
    outputs[action] = `Request failed: ${error.message}`;
  } finally {
    loadingActions[action] = false;
  }
}

export function useMatchStore() {
  return {
    bundle,
    ids,
    currentSummary,
    uploadState,
    outputs,
    loadingActions,
    actionCards,
    setFile,
    uploadBundle,
    runAction,
  };
}
