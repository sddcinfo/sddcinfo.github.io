// Astro Starlight config for an LLM-generated code wiki.
//
// This file is STATIC and committed verbatim from the sddc-cli template (pinned
// dependency versions live in package.json). Everything repo-specific - site
// URL, base path, title, and the section sidebar - is read from the generated
// `wiki.gen.json`, which `sddc repo wiki build` writes. Keeping the JS static and
// the variance in JSON is what makes the scaffold reproducible across repos.
//
// Markdown content is NOT under src/content/docs; it lives in the repo's
// `docs/wiki/` (see src/content.config.ts), so the pages stay reviewable and
// GitHub-renderable on their own.
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import gen from "./wiki.gen.json" with { type: "json" };

// Tailwind v4 is wired via PostCSS (postcss.config.mjs), not @tailwindcss/vite:
// under Astro 6's rolldown-based vite the vite plugin trips
// "Missing field `tsconfigPaths`". The PostCSS path keeps both latest Astro and
// Tailwind v4 working.
export default defineConfig({
  // Site URL comes from the WIKI_SITE env at deploy (the Pages workflow derives
  // it from the GitHub context), never hardcoded - the hosting org name must not
  // live in committed files. Falls back to gen.site (empty) for local builds.
  site: process.env.WIKI_SITE || gen.site || undefined,
  base: gen.base,
  integrations: [
    // Diagrams are pre-rendered to inline SVG at build time (D2), so there is no
    // client-side diagram runtime here.
    starlight({
      title: gen.title,
      description: gen.description,
      customCss: ["./src/styles/global.css"],
      // Drop the default page footer (pagination / last-updated / edit-link /
      // site footer line): noise on a generated, line-cited code wiki.
      components: {
        Footer: "./src/components/EmptyFooter.astro",
      },
      // Hover/tap preview for citation chips: one reused floating card shows the
      // hidden per-source code block (.cite-sources) next to the hovered <sup>.
      // Edge-flips horizontally; stays open while the pointer is over the card.
      head: [
        {
          tag: "script",
          content:
            "document.addEventListener('DOMContentLoaded',()=>{" +
            "const tip=document.createElement('div');tip.className='cite-pop';tip.hidden=true;document.body.appendChild(tip);" +
            "let h;const hide=()=>{h=setTimeout(()=>{tip.hidden=true;},180);};" +
            "const show=c=>{const s=document.getElementById(c.dataset.ref);if(!s)return;clearTimeout(h);" +
            "tip.innerHTML=s.innerHTML;tip.hidden=false;const r=c.getBoundingClientRect();" +
            "tip.style.top=(window.scrollY+r.bottom+6)+'px';tip.style.left=(window.scrollX+r.left)+'px';" +
            "const t=tip.getBoundingClientRect();if(t.right>window.innerWidth-8){" +
            "tip.style.left=Math.max(8,window.scrollX+window.innerWidth-t.width-8)+'px';}};" +
            "document.querySelectorAll('sup.cite[data-ref]').forEach(c=>{" +
            "c.addEventListener('mouseenter',()=>show(c));c.addEventListener('mouseleave',hide);" +
            "c.addEventListener('click',e=>{e.preventDefault();show(c);});});" +
            "tip.addEventListener('mouseenter',()=>clearTimeout(h));tip.addEventListener('mouseleave',hide);});",
        },
      ],
      // gen.sidebar is null for a single repo (Starlight auto-generates the nav
      // from the actual pages, so it can never point at a missing page) and a
      // grouped autogenerate list for the combined view.
      ...(gen.sidebar ? { sidebar: gen.sidebar } : {}),
      pagefind: true,
      social: gen.social ?? [],
    }),
  ],
});
