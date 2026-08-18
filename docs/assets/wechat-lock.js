(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var isWechat =
    /MicroMessenger|WeChat|wxwork/i.test(navigator.userAgent) ||
    params.get("wechat") === "1" ||
    params.get("lock") === "1" ||
    document.documentElement.getAttribute("data-lock") === "always";

  if (!isWechat) {
    return;
  }

  document.documentElement.classList.add("wechat-lock");

  document.addEventListener(
    "click",
    function (event) {
      var link = event.target && event.target.closest
        ? event.target.closest("a[href]")
        : null;
      if (!link) {
        return;
      }

      var raw = link.getAttribute("href") || "";
      if (/^(#|mailto:|tel:)/i.test(raw.trim())) {
        return;
      }

      var hrefUrl;
      try {
        hrefUrl = new URL(raw, window.location.href);
      } catch (error) {
        event.preventDefault();
        return;
      }

      if (hrefUrl.pathname !== window.location.pathname) {
        event.preventDefault();
        event.stopPropagation();
      }
    },
    true
  );
})();
