(function () {
  "use strict";

  function setSubmenu(button, open) {
    button.setAttribute("aria-expanded", String(open));
  }

  function closeAllSubmenus(root) {
    root.querySelectorAll(".site-block-navigation-submenu__toggle[aria-expanded='true']")
      .forEach(function (button) { setSubmenu(button, false); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("nav.site-block-navigation").forEach(function (navigation) {
      var container = navigation.querySelector(".site-block-navigation__responsive-container");
      var openButton = navigation.querySelector(".site-block-navigation__responsive-container-open");
      var closeButton = navigation.querySelector(".site-block-navigation__responsive-container-close");

      navigation.querySelectorAll(".site-block-navigation-submenu__toggle").forEach(function (button) {
        button.setAttribute("aria-expanded", "false");
        button.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          setSubmenu(button, button.getAttribute("aria-expanded") !== "true");
        });
      });

      if (container && openButton) {
        openButton.addEventListener("click", function () {
          container.classList.add("is-menu-open");
          container.setAttribute("aria-hidden", "false");
          document.documentElement.classList.add("has-modal-open");
          if (closeButton) closeButton.focus();
        });
      }

      if (container && closeButton) {
        closeButton.addEventListener("click", function () {
          container.classList.remove("is-menu-open");
          container.setAttribute("aria-hidden", "true");
          document.documentElement.classList.remove("has-modal-open");
          closeAllSubmenus(navigation);
          if (openButton) openButton.focus();
        });
      }

      navigation.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") return;
        closeAllSubmenus(navigation);
        if (container) container.classList.remove("is-menu-open");
        document.documentElement.classList.remove("has-modal-open");
        if (openButton) openButton.focus();
      });
    });

    document.addEventListener("click", function (event) {
      document.querySelectorAll("nav.site-block-navigation").forEach(function (navigation) {
        if (!navigation.contains(event.target)) closeAllSubmenus(navigation);
      });
    });
  });
})();
