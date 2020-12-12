"use strict";

(function () {
  $("#wpy-contribs-form-namespace > option").each(function () {
    let $option = $(this);
    let value = $option.val();

    if (!$option.text()) {
      if (value === "0") {
        $option.text(`(${wpy.config.get("wpyMainNamespaceName")})`);
      }
      if (value === "") {
        $option.html(`<b>${wpy.config.get("wpyAllNamespacesName")}</b>`)
      }
    }
  });

  let $targetUser = $("#wpy-contribs-form-target-user");
  // Remove name from target-user field as its value is only used for the action URL.
  $targetUser.attr("name", "")

  $("#wpy-contribs-form").submit(function () {
    let url = wpy.config.get("wpyUrlPath") + wpy.currentPage.getNamespaceName(true) + ":"
        + wpy.currentPage.getSpecialPageTitle(true) + "/" + $targetUser.val();
    $(this).prop("action", url);
  })
})();
