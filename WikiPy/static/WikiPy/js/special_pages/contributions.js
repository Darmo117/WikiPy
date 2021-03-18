"use strict";

(function () {
  let $targetUser = $("#wpy-contribs-form-target-user");
  // Remove name from target-user field as its value is only used for the action URL.
  $targetUser.attr("name", "")

  $("#wpy-contribs-form").submit(function () {
    let url = wpy.config.get("wpyUrlPath") + wpy.currentPage.getNamespaceName(true) + ":"
        + wpy.currentPage.getSpecialPageTitle(true) + "/" + $targetUser.val();
    $(this).prop("action", url);
  })
})();
