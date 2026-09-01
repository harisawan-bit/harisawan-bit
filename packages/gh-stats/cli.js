#!/usr/bin/env node
const https = require('https');
const http = require('http');

function fetch(url) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    mod.get(url, { headers: { 'User-Agent': 'gh-stats' } }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });
}

async function main() {
  const user = process.argv[2];
  if (!user) { console.error('usage: gh-stats <username>'); process.exit(1); }
  
  try {
    const repos = await fetch(`https://api.github.com/users/${user}/repos?per_page=100`);
    const stars = repos.reduce((s, r) => s + r.stargazers_count, 0);
    const forks = repos.reduce((s, r) => s + r.forks_count, 0);
    const langs = {};
    repos.forEach(r => { if (r.language) langs[r.language] = (langs[r.language] || 0) + 1; });
    
    console.log(`@${user}`);
    console.log(`  repos:   ${repos.length}`);
    console.log(`  stars:   ${stars}`);
    console.log(`  forks:   ${forks}`);
    console.log(`  langs:   ${Object.entries(langs).sort((a,b) => b[1]-a[1]).slice(0,5).map(([k,v]) => `${k}(${v})`).join(', ')}`);
  } catch (e) {
    console.error('error:', e.message);
    process.exit(1);
  }
}

main();
