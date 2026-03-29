<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useMatchStore } from "./composables/useMatchStore";
import UploadSection from "./components/UploadSection.vue";
import ActionPanel from "./components/ActionPanel.vue";
import ResultCard from "./components/ResultCard.vue";
import AboutAuthor from "./components/AboutAuthor.vue";

const store = useMatchStore();

const currentPage = ref("home");

const pages = {
  home: {
    label: "Workspace",
    hash: "#/",
  },
  author: {
    label: "About Author",
    hash: "#/author",
  },
};

const syncPageWithHash = () => {
  currentPage.value = window.location.hash === "#/author" ? "author" : "home";
};

const setPage = (page) => {
  window.location.hash = pages[page].hash;
};

const currentPageLabel = computed(() => pages[currentPage.value].label);

onMounted(() => {
  syncPageWithHash();
  window.addEventListener("hashchange", syncPageWithHash);
});

onUnmounted(() => {
  window.removeEventListener("hashchange", syncPageWithHash);
});
</script>

<template>
  <div class="relative overflow-hidden">
    <div class="grid-fade pointer-events-none fixed inset-0"></div>

    <main class="relative mx-auto w-[min(1180px,calc(100%-1.5rem))] py-8 md:py-12 lg:py-16">
      <header class="mb-6 flex flex-col gap-4 md:mb-8 md:flex-row md:items-center md:justify-between">
        <div>
          <p class="font-mono text-xs uppercase tracking-[0.22em] text-ember/80">RAG demo</p>
          <p class="mt-2 text-sm text-black/55">Current page: {{ currentPageLabel }}</p>
        </div>

        <nav class="inline-flex w-full gap-2 rounded-full border border-black/10 bg-white/70 p-1 md:w-auto">
          <button
            type="button"
            class="nav-pill"
            :class="{ 'nav-pill-active': currentPage === 'home' }"
            @click="setPage('home')"
          >
            Workspace
          </button>
          <button
            type="button"
            class="nav-pill"
            :class="{ 'nav-pill-active': currentPage === 'author' }"
            @click="setPage('author')"
          >
            About Author
          </button>
        </nav>
      </header>

      <template v-if="currentPage === 'home'">
        <section class="mb-6 md:mb-8">
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
      </template>

      <AboutAuthor v-else />
    </main>
  </div>
</template>
