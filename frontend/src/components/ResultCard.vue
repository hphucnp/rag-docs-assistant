<script setup>
import { computed } from "vue";
import { marked } from "marked";
import { useMatchStore } from "../composables/useMatchStore";

const props = defineProps({
  card: {
    type: Object,
    required: true,
  },
});

const store = useMatchStore();

const parsedMarkdown = computed(() => {
  const content = store.outputs[props.card.key] || "";
  return marked.parse(content);
});
</script>

<template>
  <article
    class="glass-panel"
    :class="{ 'lg:col-span-2': card.key === 'highlight-achievements' }"
  >
    <div class="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
      <h3 class="text-xl font-bold tracking-[-0.03em]">{{ card.title }}</h3>
      <span class="font-mono text-xs text-black/45">{{ card.subtitle }}</span>
    </div>
    
    <div 
      class="result-box prose max-w-none prose-sm sm:prose-base prose-headings:font-bold prose-a:text-ember focus:outline-none" 
      v-html="parsedMarkdown"
    ></div>
  </article>
</template>

<style scoped>
/* Ghi đè CSS mặc định để tích hợp chung lớp result-box vào bên trong markdown */
.result-box {
  @apply min-h-[260px] rounded-3xl border border-black/10 bg-white/60 p-5 overflow-x-auto;
}
</style>
