document.addEventListener("DOMContentLoaded", () => {
  document.body.classList.add("fade-in");

  const profileWrap = document.getElementById("fnProfileWrap");
  const profileTrigger = document.getElementById("fnProfileTrigger");
  const profileMenu = document.getElementById("fnProfileMenu");
  if (profileWrap && profileTrigger && profileMenu) {
    const closeMenu = () => {
      profileMenu.hidden = true;
      profileTrigger.setAttribute("aria-expanded", "false");
      profileWrap.classList.remove("is-open");
    };
    const openMenu = () => {
      profileMenu.hidden = false;
      profileTrigger.setAttribute("aria-expanded", "true");
      profileWrap.classList.add("is-open");
    };
    const toggleMenu = () => {
      if (profileMenu.hidden) openMenu();
      else closeMenu();
    };
    profileTrigger.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleMenu();
    });
    document.addEventListener("click", (e) => {
      if (!profileWrap.contains(e.target)) closeMenu();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeMenu();
    });
  }

  const reveals = document.querySelectorAll(".scroll-reveal");
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add("visible");
    });
  });
  reveals.forEach((el) => observer.observe(el));

  const timers = document.querySelectorAll("[data-countdown]");
  timers.forEach((timer) => {
    const endDate = new Date(timer.dataset.countdown);
    const update = () => {
      const diff = endDate - new Date();
      if (diff <= 0) {
        timer.textContent = "Акция завершена";
        return;
      }
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
      const minutes = Math.floor((diff / (1000 * 60)) % 60);
      const seconds = Math.floor((diff / 1000) % 60);
      timer.textContent = `${days}д ${hours}ч ${minutes}м ${seconds}с`;
    };
    update();
    setInterval(update, 1000);
  });

  const toasts = document.querySelectorAll(".toast");
  toasts.forEach((toastEl) => {
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
  });

  const serviceModalEl = document.getElementById("fnServiceModal");
  if (serviceModalEl && typeof bootstrap !== "undefined") {
    const serviceModal = bootstrap.Modal.getOrCreateInstance(serviceModalEl, {
      focus: true,
      backdrop: true,
    });
    const titleEl = document.getElementById("fnServiceModalTitle");
    const categoryEl = document.getElementById("fnServiceModalCategory");
    const priceEl = document.getElementById("fnServiceModalPrice");
    const durationTextEl = document.getElementById("fnServiceModalDurationText");
    const durationWrapEl = document.getElementById("fnServiceModalDuration");
    const descEl = document.getElementById("fnServiceModalDesc");
    const mediaWrap = document.getElementById("fnServiceModalMedia");
    const imgEl = document.getElementById("fnServiceModalImg");

    const getServiceDescription = (id) => {
      const source = document.querySelector(
        `.fn-service-detail-desc[data-for-service="${id}"]`
      );
      if (!source) return "";
      if (source.tagName === "TEMPLATE" && source.content) {
        return source.content.textContent.trim();
      }
      return source.textContent.trim();
    };

    document.body.addEventListener("click", (e) => {
      const btn = e.target.closest(".fn-service-detail-trigger");
      if (!btn) return;

      const id = btn.dataset.serviceId;
      const description = getServiceDescription(id);
      const cardDesc = btn
        .closest(".fn-home-service-card")
        ?.querySelector(".fn-home-service-card__desc")
        ?.textContent?.trim();

      if (titleEl) titleEl.textContent = btn.dataset.name || "";
      if (priceEl) {
        priceEl.textContent = btn.dataset.price ? `${btn.dataset.price} ₽` : "";
      }
      if (durationTextEl && durationWrapEl) {
        const minutes = btn.dataset.duration;
        if (minutes) {
          durationTextEl.textContent = `${minutes} мин`;
          durationWrapEl.hidden = false;
        } else {
          durationTextEl.textContent = "";
          durationWrapEl.hidden = true;
        }
      }
      if (descEl) {
        descEl.textContent =
          description || cardDesc || "Описание скоро появится.";
      }

      const category = (btn.dataset.category || "").trim();
      if (categoryEl) {
        if (category) {
          categoryEl.textContent = category;
          categoryEl.hidden = false;
        } else {
          categoryEl.textContent = "";
          categoryEl.hidden = true;
        }
      }

      const imageUrl = (btn.dataset.image || "").trim();
      if (mediaWrap && imgEl) {
        if (imageUrl) {
          imgEl.src = imageUrl;
          imgEl.alt = btn.dataset.name || "Услуга";
          mediaWrap.hidden = false;
        } else {
          imgEl.removeAttribute("src");
          mediaWrap.hidden = true;
        }
      }

      serviceModal.show();
    });
  }

});
