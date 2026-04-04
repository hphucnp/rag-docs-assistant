<script setup>
import { useMatchStore } from "../composables/useMatchStore";

const store = useMatchStore();
const currentSummary = store.currentSummary;
</script>

<template>
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
        <input v-model="store.ids.cvId" class="field-shell" type="text" placeholder="Generated after upload" />
      </label>

      <label class="block">
        <span class="mb-2 block text-sm text-black/60">JD ID</span>
        <input v-model="store.ids.jdId" class="field-shell" type="text" placeholder="Generated after upload" />
      </label>

      <label class="block">
        <span class="mb-2 block text-sm text-black/60">Notes ID</span>
        <input v-model="store.ids.notesId" class="field-shell" type="text" placeholder="Optional" />
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
        v-for="card in store.actionCards"
        :key="card.key"
        type="button"
        class="ghost-button"
        :disabled="store.loadingActions[card.key]"
        @click="store.runAction(card.key)"
      >
        {{ store.loadingActions[card.key] ? card.loading : card.button }}
      </button>
    </div>
  </section>
</template>
