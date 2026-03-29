<script setup>
import { computed } from "vue";
import { useMatchStore } from "../composables/useMatchStore";

const store = useMatchStore();

const statusClasses = computed(() => {
  if (store.uploadState.variant === "success") {
    return "border-moss/25 bg-moss/10 text-moss";
  }

  if (store.uploadState.variant === "error") {
    return "border-ember/25 bg-ember/10 text-ember";
  }

  return "border-black/10 bg-white/60 text-black/60";
});
</script>

<template>
  <section class="glass-panel">
    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <div>
        <p class="font-mono text-xs uppercase tracking-[0.18em] text-ember/80">Step 1</p>
        <h2 class="mt-2 text-2xl font-bold tracking-[-0.03em]">Upload Bundle</h2>
      </div>
      <p class="font-mono text-xs text-black/45">POST /api/v1/match/upload-bundle</p>
    </div>

    <form class="mt-6 grid gap-4 md:grid-cols-2" @submit.prevent="store.uploadBundle">
      <label class="block">
        <span class="mb-2 block text-sm text-black/60">CV file</span>
        <input class="field-shell" type="file" accept=".pdf,.txt,.md" required @change="store.setFile($event, 'cvFile')" />
      </label>

      <label class="block">
        <span class="mb-2 block text-sm text-black/60">Job description file</span>
        <input class="field-shell" type="file" accept=".pdf,.txt,.md" required @change="store.setFile($event, 'jdFile')" />
      </label>

      <label class="block">
        <span class="mb-2 block text-sm text-black/60">CV title</span>
        <input v-model="store.bundle.cvTitle" class="field-shell" type="text" />
      </label>

      <label class="block">
        <span class="mb-2 block text-sm text-black/60">JD title</span>
        <input v-model="store.bundle.jdTitle" class="field-shell" type="text" />
      </label>

      <label class="block md:col-span-2">
        <span class="mb-2 block text-sm text-black/60">Notes</span>
        <textarea
          v-model="store.bundle.notes"
          class="field-shell min-h-32 resize-y"
          rows="4"
          placeholder="Optional: recruiter notes, target story, skills to emphasize, salary concerns..."
        ></textarea>
      </label>

      <div class="md:col-span-2">
        <button class="primary-button w-full md:w-auto" type="submit" :disabled="store.uploadState.loading">
          {{ store.uploadState.loading ? "Uploading..." : "Upload bundle" }}
        </button>
      </div>
    </form>

    <div class="mt-5 whitespace-pre-wrap rounded-[22px] border px-4 py-4 font-mono text-sm" :class="statusClasses">
      {{ store.uploadState.message }}
    </div>
  </section>
</template>
