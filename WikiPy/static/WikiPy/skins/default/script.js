(function () {
  // User link popups
  $(".wpy-user-link-tooltip-btn[data-toggle='popover']").each(function () {
    let $button = $(this);
    let $userLink = $("#" + $button.data("user-link"));

    $button.popover({
      trigger: "focus",
      placement: "top",
      html: true,
      title: wpy.translate("popover.user.title." + $userLink.data("user-gender"),
          {username: $userLink.data("user-name")}),
      content: function () {
        function getItem(page, params, exists, key) {
          let classes = exists ? "" : "wpy-redlink";
          let url = wpy.config.get("wpyUrlPath") + wpy.encodePageTitleUrl(page) + (params ? "?" + params : "");
          let text = wpy.translate("popover.user." + key)
          let tooltip = page + (exists ? "" : ` (${wpy.translate("redlink_tooltip")})`);
          return `<li><a href="${url}" title="${tooltip}" class="${classes}">${text}</a></li>`;
        }

        let items = [
          getItem($userLink.data("user-page"), $userLink.data("user-page-params"), $userLink.data("user-page-exists"), "page"),
          getItem($userLink.data("user-talk-page"), $userLink.data("user-talk-page-params"), $userLink.data("user-talk-page-exists"), "talk_page"),
          getItem($userLink.data("user-contributions-page"), $userLink.data("user-contributions-page-params"), $userLink.data("user-contributions-page-exists"), "contributions_page"),
        ];
        for (let k of $userLink.data("user-pages").split(" ")) {
          items.push(getItem($userLink.data(`user-${k}-page`), $userLink.data(`user-${k}-page-params`), $userLink.data(`user-${k}-page-exists`), k.replace("-", "_")));
        }
        return `<ul class="wpy-user-pages">${items.join("")}</ul>`;
      },
    });
    $button.attr("title", wpy.translate("popover.user.tooltip"));
  });

  // Page layout resize
  function updatePageLayout() {
    if (window.innerWidth <= 1224) {
      $("#wpy-nav-bar-right").insertAfter($("#wpy-nav-bar-left"));
    } else {
      $("#wpy-center-col").next().append($("#wpy-nav-bar-right"));
    }
  }

  updatePageLayout();
  $(window).resize(updatePageLayout);
})();
