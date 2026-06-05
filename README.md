# sddcinfo.github.io

The sddc.info landing page: an index of the public project wikis, served at
[sddcinfo.github.io](https://sddcinfo.github.io/). Built with Astro, Starlight,
and Tailwind v4 (the same stack each project wiki uses) and deployed to GitHub
Pages by `.github/workflows/deploy.yml`.

## Develop

```bash
npm ci
npm run dev      # local preview
npm run build    # production build into dist/
```

The page content is `src/content/docs/index.mdx`. Editing standards match the
project repos (no em-dashes or en-dashes, no AI-speak, no operator identity, no
broken links); `.githooks/pre-push` enforces them. Enable the hook once with:

```bash
git config core.hooksPath .githooks
```
