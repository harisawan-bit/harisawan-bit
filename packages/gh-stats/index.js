module.exports = function ghStats(user) {
  const https = require('https');
  return new Promise((resolve, reject) => {
    https.get(`https://api.github.com/users/${user}/repos?per_page=100`, {
      headers: { 'User-Agent': 'gh-stats' }
    }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        const repos = JSON.parse(data);
        resolve({
          repos: repos.length,
          stars: repos.reduce((s, r) => s + r.stargazers_count, 0),
          forks: repos.reduce((s, r) => s + r.forks_count, 0),
          langs: repos.reduce((l, r) => { if (r.language) l[r.language] = (l[r.language] || 0) + 1; return l; }, {})
        });
      });
    }).on('error', reject);
  });
};
