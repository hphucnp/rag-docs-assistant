<script setup>
import { useMatchStore } from "./composables/useMatchStore";
import UploadSection from "./components/UploadSection.vue";
import ActionPanel from "./components/ActionPanel.vue";
import ResultCard from "./components/ResultCard.vue";

const store = useMatchStore();
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

      <UploadSection />
      
      <ActionPanel />

      <section class="mt-6 grid gap-6 lg:grid-cols-2">
        <ResultCard
          v-for="card in store.actionCards"
          :key="card.key"
          :card="card"
        />
      </section>
    </main>
  </div>
</template>
