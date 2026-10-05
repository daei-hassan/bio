// Remembers the chapter and scroll position last read, in this browser only,
// separately for each language.
(function () {
  var lang = document.documentElement.lang;
  var KEY = "zendegi-nameh-last" + (lang === "fa" ? "" : "-" + lang);

  function read() {
    try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch (e) { return null; }
  }
  function write(value) {
    try { localStorage.setItem(KEY, JSON.stringify(value)); } catch (e) { /* private mode */ }
  }

  var chapter = Number(document.body.dataset.chapter || 0);

  if (chapter) {
    var scrollable = function () {
      return Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    };
    var last = read();
    if (location.hash === "#edame" && last && last.chapter === chapter) {
      window.scrollTo(0, last.at * scrollable());
    }
    var timer = null;
    var save = function () {
      timer = null;
      write({ chapter: chapter, title: document.body.dataset.title, at: window.scrollY / scrollable() });
    };
    save();
    window.addEventListener("scroll", function () {
      if (!timer) timer = setTimeout(save, 400);
    }, { passive: true });

    // Close the contents menu when clicking elsewhere
    var menu = document.querySelector(".contents");
    document.addEventListener("click", function (e) {
      if (menu && menu.open && !menu.contains(e.target)) menu.open = false;
    });
  } else {
    var saved = read();
    var start = document.getElementById("start");
    if (saved && saved.chapter && start) {
      start.href = start.dataset.prefix + "-" + saved.chapter + ".html#edame";
      start.textContent = start.dataset.resume + ": " + saved.title;
    }
  }
})();
