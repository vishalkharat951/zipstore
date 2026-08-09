(function () {
  'use strict';
  var MIN_VISIBLE = 700;
  var MAX_WAIT = 6000;
  var loader = document.getElementById('app-loader');
  var started = Date.now();

  if (!loader) return;

  function hide() {
    if (!loader || loader.classList.contains('loader-hidden')) return;
    loader.classList.add('loader-hidden');
    setTimeout(function () {
      if (loader && loader.parentNode) loader.parentNode.removeChild(loader);
    }, 600);
  }

  function maybeHide() {
    var elapsed = Date.now() - started;
    var remaining = MIN_VISIBLE - elapsed;
    if (remaining <= 0) {
      hide();
    } else {
      setTimeout(hide, remaining);
    }
  }

  if (document.readyState === 'complete') {
    maybeHide();
  } else {
    window.addEventListener('load', maybeHide);
    setTimeout(function () {
      if (!loader.classList.contains('loader-hidden')) hide();
    }, MAX_WAIT);
  }
})();
