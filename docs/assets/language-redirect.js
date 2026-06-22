(function () {
  var storageKey = "py-libterraform-docs-language";
  var productionOrigin = "https://prodesire.github.io";
  var productionBasePath = "/py-libterraform";
  var params = new URLSearchParams(window.location.search);
  var requestedLanguage = params.get("lang");

  function isLocalPreview() {
    var hostname = window.location.hostname;
    return (
      hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1"
    );
  }

  function currentPreviewPathname() {
    var pathname = window.location.pathname || "/";
    if (pathname === productionBasePath) {
      return "/";
    }
    if (pathname.indexOf(productionBasePath + "/") === 0) {
      pathname = pathname.slice(productionBasePath.length);
    }
    return pathname || "/";
  }

  function localPreviewHref(href, targetLanguage) {
    var url;
    try {
      url = new URL(href, window.location.href);
    } catch (_) {
      return null;
    }

    if (
      url.origin !== productionOrigin ||
      url.pathname.indexOf(productionBasePath) !== 0
    ) {
      return null;
    }

    var targetPathname = currentPreviewPathname();
    if (
      targetLanguage === "zh" &&
      targetPathname !== "/zh" &&
      targetPathname.indexOf("/zh/") !== 0
    ) {
      targetPathname = "/zh" + targetPathname;
    } else if (targetLanguage === "en") {
      if (targetPathname === "/zh") {
        targetPathname = "/";
      } else if (targetPathname.indexOf("/zh/") === 0) {
        targetPathname = targetPathname.slice(3) || "/";
      }
    }
    return targetPathname + url.search + url.hash;
  }

  function rewriteLanguageAlternates() {
    if (!isLocalPreview()) {
      return;
    }

    var nodes = document.querySelectorAll(
      'a.md-select__link[href], link[rel="alternate"][href]'
    );
    nodes.forEach(function (node) {
      var href = localPreviewHref(
        node.getAttribute("href"),
        node.getAttribute("hreflang")
      );
      if (href) {
        node.setAttribute("href", href);
      }
    });
  }

  rewriteLanguageAlternates();

  if (requestedLanguage === "en" || requestedLanguage === "zh") {
    try {
      window.localStorage.setItem(storageKey, requestedLanguage);
    } catch (_) {
      // Ignore storage failures; explicit links should still load normally.
    }
    return;
  }

  var pathname = window.location.pathname.replace(/\/+$/, "/");
  var isEnglishRoot = pathname === "/" || /\/py-libterraform\/$/.test(pathname);

  if (!isEnglishRoot) {
    return;
  }

  var preferredLanguage = null;
  try {
    preferredLanguage = window.localStorage.getItem(storageKey);
  } catch (_) {
    preferredLanguage = null;
  }

  if (preferredLanguage === "en") {
    return;
  }

  var languages = window.navigator.languages || [
    window.navigator.language || window.navigator.userLanguage || "",
  ];
  var wantsChinese =
    preferredLanguage === "zh" ||
    languages.some(function (language) {
      language = String(language).toLowerCase();
      return language.indexOf("zh") === 0;
    });

  if (wantsChinese) {
    window.location.replace(new URL("zh/", window.location.href).toString());
  }
})();
