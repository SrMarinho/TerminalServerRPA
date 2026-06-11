// Theme bootstrap — loaded synchronously in <head> so the data-theme attribute
// is set before first paint (no flash of wrong theme).
(function(){
  try {
    var stored = localStorage.getItem('TerminalServerRPA.theme');
    var theme = stored || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    if (!stored) { try { localStorage.setItem('TerminalServerRPA.theme', theme); } catch(e) {} }
  } catch(e) {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();
