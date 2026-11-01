import { cpSync, rmSync } from 'node:fs';
const root = new URL('../',import.meta.url);
const destination = new URL('site/workspace-generated/',root);
rmSync(destination,{recursive:true,force:true});
cpSync(new URL('src/',root),destination,{recursive:true});
