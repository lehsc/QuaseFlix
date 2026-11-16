/* Load the adaptive player only when the real backend can return a manifest. */
window.QuaseflixShakaReady = (() => {
  if (window.QuaseflixPagesDemo?.active) return Promise.resolve(false);
  return new Promise(resolve => {
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/shaka-player@5.3.4/dist/shaka-player.compiled.min.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.head.append(script);
  });
})();
