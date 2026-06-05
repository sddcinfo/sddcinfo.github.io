// @ts-check
import { defineConfig, fontProviders } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

// Static output for GitHub Pages. Same design stack as the sddc.info website
// (Astro + Tailwind v4 + Inter), minus the Cloudflare adapter.
export default defineConfig({
  site: 'https://sddcinfo.github.io',
  base: '/',
  integrations: [sitemap()],
  fonts: [{
    provider: fontProviders.google(),
    name: 'Inter',
    cssVariable: '--font-inter',
    weights: [400, 500, 600, 700],
    display: 'block',
  }],
  trailingSlash: 'ignore',
  compressHTML: true,
  vite: {
    plugins: [tailwindcss()],
  },
});
