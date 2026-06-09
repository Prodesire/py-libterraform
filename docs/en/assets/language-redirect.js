(function () {
  var storageKey = "py-libterraform-docs-language";
  var params = new URLSearchParams(window.location.search);
  var requestedLanguage = params.get("lang");

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
