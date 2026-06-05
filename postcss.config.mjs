// Tailwind v4 via PostCSS. Astro picks this up automatically and runs it over
// the Starlight customCss (src/styles/global.css). Used instead of
// @tailwindcss/vite because that plugin is incompatible with Astro 6's
// rolldown-based vite. Pinned versions live in package.json.
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
