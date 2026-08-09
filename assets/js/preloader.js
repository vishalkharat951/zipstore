(function () {
  'use strict';

  var preloader = document.getElementById('zip-preloader');
  if (!preloader) return;

  var FADE_MS = 500;
  var FAILSAFE_MS = 20000;
  var DOTS_STATES = ['', '.', '..', '...'];

  var docEl = document.documentElement;
  docEl.classList.add('zip-preloader-active');

  var dotsEl = preloader.querySelector('.zip-preloader__dots');
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var dotsTimer = null;
  var dotsIndex = 0;

  if (dotsEl && !reduceMotion) {
    dotsTimer = window.setInterval(function () {
      dotsIndex = (dotsIndex + 1) % DOTS_STATES.length;
      dotsEl.textContent = DOTS_STATES[dotsIndex];
    }, 400);
  }

  var hidden = false;

  function hide() {
    if (hidden) return;
    hidden = true;

    if (dotsTimer) {
      window.clearInterval(dotsTimer);
      dotsTimer = null;
    }

    docEl.classList.remove('zip-preloader-active');
    preloader.classList.add('zip-preloader--hidden');

    window.setTimeout(function () {
      if (preloader.parentNode) {
        preloader.parentNode.removeChild(preloader);
      }
    }, FADE_MS + 150);
  }

  if (document.readyState === 'complete') {
    hide();
  } else {
    window.addEventListener('load', hide);
    window.setTimeout(hide, FAILSAFE_MS);
  }
})();
