"use strict";

(function () {
  $("#wpy-diff-form").submit(function () {
    let revid1 = $("#wpy-diff-form-revisionid1").val();
    let revid2 = $("#wpy-diff-form-revisionid2").val();
    this.action = wpy.config.get("wpyUrlPath") + wpy.currentPage.getFullTitle(true) + `/${revid1}/${revid2}`;
  })
})();
