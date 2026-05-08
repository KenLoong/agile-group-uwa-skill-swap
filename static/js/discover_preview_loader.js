(() => {
  function loadCategory(slug) {
    const grid = document.getElementById("post-grid");
    if (!grid) {
      return;
    }
    grid.innerHTML = "";
    const q = slug === "all" ? "category=all" : "category=" + encodeURIComponent(slug);
    fetch("/api/filter?" + q + "&sort=newest&page=1")
      .then((res) => res.json())
      .then((data) => {
        const posts = data.posts || [];
        posts.forEach((p) => {
          const col = document.createElement("div");
          col.className = "col-md-6 col-xl-4";
          const art = document.createElement("article");
          art.className = "card h-100 shadow-sm";
          art.innerHTML =
            '<div class="card-body">' +
              '<p class="text-uppercase small text-muted mb-1 cat-line"></p>' +
              '<h2 class="h6 card-title"></h2>' +
              '<p class="small text-secondary mb-0 card-text"></p>' +
            "</div>";
          const catEl = art.querySelector(".cat-line");
          if (catEl) {
            catEl.textContent = p.category_label || "";
          }
          const titleEl = art.querySelector(".card-title");
          if (titleEl) {
            titleEl.textContent = p.title || "";
          }
          const snipEl = art.querySelector(".card-text");
          if (snipEl) {
            snipEl.textContent = p.snippet || "";
          }
          col.appendChild(art);
          grid.appendChild(col);
        });
      })
      .catch(() => {
        grid.textContent = "Could not load listings.";
      });
  }

  document.querySelectorAll("button[data-category]").forEach((btn) => {
    btn.addEventListener("click", () => {
      loadCategory(btn.getAttribute("data-category") || "all");
    });
  });

  loadCategory("all");
})();
