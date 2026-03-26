<script setup>
import { computed, reactive, ref } from "vue";

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

const statusClasses = computed(() => {
  if (uploadState.variant === "success") {
    return "border-moss/25 bg-moss/10 text-moss";
  }

  if (uploadState.variant === "error") {
    return "border-ember/25 bg-ember/10 text-ember";
  }

  return "border-black/10 bg-white/60 text-black/60";
});

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
</script>

<template>
  <div class="relative overflow-hidden">
    <div class="grid-fade pointer-events-none fixed inset-0"></div>

    <main class="relative mx-auto w-[min(1180px,calc(100%-1.5rem))] py-8 md:py-12 lg:py-16">
      <section class="mb-6 md:mb-8">
        <p class="font-mono text-xs uppercase tracking-[0.22em] text-ember/80">RAG demo</p>
        <div class="mt-4 grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)] lg:items-end">
          <div>
            <h1 class="max-w-[10ch] text-5xl font-bold leading-[0.92] tracking-[-0.05em] md:text-7xl">
              CV / Job Description Match
            </h1>
            <p class="mt-5 max-w-2xl text-base leading-8 text-black/65 md:text-lg">
              Upload a resume, a job description, and optional recruiter notes. Then trigger the
              three outputs that matter in a hiring workflow: missing skills, rewritten summary,
              and the achievements worth surfacing first.
            </p>
          </div>

          <div class="glass-panel relative overflow-hidden">
            <div class="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-ember via-orange-300 to-moss"></div>
            <div class="font-mono text-xs uppercase tracking-[0.18em] text-black/45">Output pack</div>
            <div class="mt-4 flex flex-wrap gap-3 text-sm">
              <span class="rounded-full border border-black/10 bg-white/75 px-4 py-2">Missing skills</span>
              <span class="rounded-full border border-black/10 bg-white/75 px-4 py-2">Rewrite summary</span>
              <span class="rounded-full border border-black/10 bg-white/75 px-4 py-2">Highlight wins</span>
            </div>
          </div>
        </div>
      </section>

      <section class="glass-panel">
        <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p class="font-mono text-xs uppercase tracking-[0.18em] text-ember/80">Step 1</p>
            <h2 class="mt-2 text-2xl font-bold tracking-[-0.03em]">Upload Bundle</h2>
          </div>
          <p class="font-mono text-xs text-black/45">POST /api/v1/match/upload-bundle</p>
        </div>

        <form class="mt-6 grid gap-4 md:grid-cols-2" @submit.prevent="uploadBundle">
          <label class="block">
            <span class="mb-2 block text-sm text-black/60">CV file</span>
            <input class="field-shell" type="file" accept=".pdf,.txt,.md" required @change="setFile($event, 'cvFile')" />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm text-black/60">Job description file</span>
            <input class="field-shell" type="file" accept=".pdf,.txt,.md" required @change="setFile($event, 'jdFile')" />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm text-black/60">CV title</span>
            <input v-model="bundle.cvTitle" class="field-shell" type="text" />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm text-black/60">JD title</span>
            <input v-model="bundle.jdTitle" class="field-shell" type="text" />
          </label>

          <label class="block md:col-span-2">
            <span class="mb-2 block text-sm text-black/60">Notes</span>
            <textarea
              v-model="bundle.notes"
              class="field-shell min-h-32 resize-y"
              rows="4"
              placeholder="Optional: recruiter notes, target story, skills to emphasize, salary concerns..."
            ></textarea>
          </label>

          <div class="md:col-span-2">
            <button class="primary-button w-full md:w-auto" type="submit" :disabled="uploadState.loading">
              {{ uploadState.loading ? "Uploading..." : "Upload bundle" }}
            </button>
          </div>
        </form>

        <div class="mt-5 whitespace-pre-wrap rounded-[22px] border px-4 py-4 font-mono text-sm" :class="statusClasses">
          {{ uploadState.message }}
        </div>
      </section>

      <section class="glass-panel mt-6">
        <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p class="font-mono text-xs uppercase tracking-[0.18em] text-ember/80">Step 2</p>
            <h2 class="mt-2 text-2xl font-bold tracking-[-0.03em]">Generate Match Outputs</h2>
          </div>
          <p class="font-mono text-xs text-black/45">Powered by stored CV / JD / notes IDs</p>
        </div>

        <div class="mt-6 grid gap-4 md:grid-cols-3">
          <label class="block">
            <span class="mb-2 block text-sm text-black/60">CV ID</span>
            <input v-model="ids.cvId" class="field-shell" type="text" placeholder="Generated after upload" />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm text-black/60">JD ID</span>
            <input v-model="ids.jdId" class="field-shell" type="text" placeholder="Generated after upload" />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm text-black/60">Notes ID</span>
            <input v-model="ids.notesId" class="field-shell" type="text" placeholder="Optional" />
          </label>
        </div>

        <label class="mt-4 block">
          <span class="mb-2 block text-sm text-black/60">Current summary</span>
          <textarea
            v-model="currentSummary"
            class="field-shell min-h-28 resize-y"
            rows="3"
            placeholder="Optional: paste the candidate's current CV summary before rewriting"
          ></textarea>
        </label>

        <div class="mt-5 grid gap-4 lg:grid-cols-3">
          <button
            v-for="card in actionCards"
            :key="card.key"
            type="button"
            class="ghost-button"
            :disabled="loadingActions[card.key]"
            @click="runAction(card.key)"
          >
            {{ loadingActions[card.key] ? card.loading : card.button }}
          </button>
        </div>
      </section>

      <section class="mt-6 grid gap-6 lg:grid-cols-2">
        <article
          v-for="card in actionCards"
          :key="card.key"
          class="glass-panel"
          :class="{ 'lg:col-span-2': card.key === 'highlight-achievements' }"
        >
          <div class="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <h3 class="text-xl font-bold tracking-[-0.03em]">{{ card.title }}</h3>
            <span class="font-mono text-xs text-black/45">{{ card.subtitle }}</span>
          </div>
          <pre class="result-box">{{ outputs[card.key] }}</pre>
        </article>
      </section>
    </main>
  </div>
</template>
