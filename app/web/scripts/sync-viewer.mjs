// Sao chép viewer/ (Three.js, một file HTML + models) vào public/viewer để dashboard dùng lại nguyên bản.
import { cpSync, mkdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, '../../../viewer');
const dst = resolve(here, '../public/viewer');
if (!existsSync(src)) { console.error('không thấy ' + src); process.exit(1); }
mkdirSync(dst, { recursive: true });
cpSync(src, dst, { recursive: true });
console.log('viewer -> public/viewer');
