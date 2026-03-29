<template>
  <section class="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
    <article class="glass-panel relative overflow-hidden">
      <div class="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-moss via-amber-400 to-ember"></div>
      <p class="font-mono text-xs uppercase tracking-[0.18em] text-moss">Author</p>
      <h1 class="mt-4 max-w-[12ch] text-5xl font-bold leading-[0.95] tracking-[-0.05em] md:text-6xl">
        Phuc Nguyen
      </h1>
      <p class="mt-5 max-w-2xl text-base leading-8 text-black/65 md:text-lg">
        Builder of this RAG Docs Assistant. This project combines FastAPI, vector search, and a
        focused Vue interface to turn document matching into a practical workflow instead of a
        backend-only demo.
      </p>

      <div class="mt-8 grid gap-4 md:grid-cols-2">
        <div class="rounded-[24px] border border-black/10 bg-white/70 p-5">
          <p class="font-mono text-xs uppercase tracking-[0.18em] text-black/45">Focus</p>
          <p class="mt-3 text-sm leading-7 text-black/70">
            AI-assisted document workflows, retrieval systems, and product-shaped backend tools
            that are usable by non-engineers.
          </p>
        </div>
        <div class="rounded-[24px] border border-black/10 bg-white/70 p-5">
          <p class="font-mono text-xs uppercase tracking-[0.18em] text-black/45">Built Here</p>
          <p class="mt-3 text-sm leading-7 text-black/70">
            Async FastAPI services, provider-based embeddings and chat integrations, PostgreSQL
            with pgvector, Docker deployment, and this Vue frontend.
          </p>
        </div>
      </div>
    </article>

    <aside class="grid gap-6">
      <section class="glass-panel">
        <p class="font-mono text-xs uppercase tracking-[0.18em] text-ember/80">Contact</p>
        <div class="mt-4 space-y-4 text-sm text-black/70">
          <div>
            <p class="text-black/45">Email</p>
            <a class="inline-block pt-1 font-semibold text-ink underline decoration-ember/40 underline-offset-4" href="mailto:hphuc.np@gmail.com">
              hphuc.np@gmail.com
            </a>
          </div>
          <div>
            <p class="text-black/45">Project</p>
            <p class="pt-1 font-semibold text-ink">RAG Docs Assistant</p>
          </div>
        </div>
      </section>

      <section class="glass-panel">
        <p class="font-mono text-xs uppercase tracking-[0.18em] text-ember/80">Project Snapshot</p>
        <div class="mt-4 flex flex-wrap gap-3 text-sm">
          <span class="rounded-full border border-black/10 bg-white/75 px-4 py-2">FastAPI</span>
          <span class="rounded-full border border-black/10 bg-white/75 px-4 py-2">Vue 3</span>
          <span class="rounded-full border border-black/10 bg-white/75 px-4 py-2">pgvector</span>
          <span class="rounded-full border border-black/10 bg-white/75 px-4 py-2">OpenAI / Groq / Ollama</span>
          <span class="rounded-full border border-black/10 bg-white/75 px-4 py-2">Docker</span>
        </div>
      </section>

      <section class="glass-panel">
        <p class="font-mono text-xs uppercase tracking-[0.18em] text-ember/80">Why This Page</p>
        <p class="mt-4 text-sm leading-7 text-black/70">
          It gives the frontend a human layer: who made the app, what kind of work it represents,
          and how to contact the author behind the product.
        </p>
      </section>
    </aside>
  </section>
</template>
