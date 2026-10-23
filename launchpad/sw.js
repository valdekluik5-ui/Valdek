// Network first: always ask the server for the newest version (skipping the browser's 10-minute cache), fall back to the last copy when offline.
const CACHE='launchpad-v2';
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
  const req=e.request;
  if(req.method!=='GET'||new URL(req.url).origin!==location.origin) return;
  e.respondWith(fetch(new Request(req.url,{cache:'no-cache',credentials:'same-origin'})).then(res=>{
    if(res.ok){ const copy=res.clone(); caches.open(CACHE).then(c=>c.put(req,copy)); }
    return res;
  }).catch(()=>caches.match(req).then(m=>m||caches.match('./'))));
});
