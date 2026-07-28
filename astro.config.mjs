// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { posts } from './src/data/posts.js';

const latestPostDate = posts.reduce(
  (latest, post) => (new Date(post.date) > new Date(latest) ? post.date : latest),
  posts[0].date
);
const latestLastmod = new Date(latestPostDate).toISOString();

export default defineConfig({
  site: 'https://danielvegabooks.com',
  trailingSlash: 'always',
  integrations: [
    sitemap({
      changefreq: 'weekly',
      serialize(item) {
        const path = new URL(item.url).pathname;

        if (path === '/') {
          return { ...item, priority: 1.0, lastmod: latestLastmod };
        }

        if (path === '/blog/') {
          return { ...item, priority: 0.8, lastmod: latestLastmod };
        }

        if (path.startsWith('/blog/')) {
          const slug = path.split('/').filter(Boolean)[1];
          const post = posts.find((p) => p.slug === slug);
          return {
            ...item,
            priority: 0.7,
            lastmod: post ? new Date(post.date).toISOString() : latestLastmod,
          };
        }

        return { ...item, priority: 0.6, lastmod: latestLastmod };
      },
    }),
  ],
});
