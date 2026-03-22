import { appendFileSync } from 'node:fs';

const raw = (process.env.PAGES_SITE_URL || '').trim();
if (!raw) {
	console.error('PAGES_SITE_URL is empty');
	process.exit(1);
}

let urlString = raw;
if (!/^https?:\/\//i.test(urlString)) {
	urlString = `https://${urlString}`;
}

let u;
try {
	u = new URL(urlString);
} catch (e) {
	console.error('Invalid PAGES_SITE_URL:', e instanceof Error ? e.message : e);
	process.exit(1);
}

let path = u.pathname.replace(/\/+$/, '') || '';
if (path === '/') {
	path = '';
}
const basePath = path === '' ? '' : path.startsWith('/') ? path : `/${path}`;
const host = u.hostname.toLowerCase();
const isGithubIo = host === 'github.io' || host.endsWith('.github.io');
const cnameHost = isGithubIo ? '' : host;

const out = process.env.GITHUB_OUTPUT;
if (!out) {
	console.log(JSON.stringify({ basePath, cnameHost }, null, 2));
	process.exit(0);
}

appendFileSync(out, `base_path=${basePath}\n`);
appendFileSync(out, `cname_host=${cnameHost}\n`);
