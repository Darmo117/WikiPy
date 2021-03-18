"use strict";

(function () {
  let idPrefix = "wpy-prefs-form-";
  let idSuffix = "-tab";

  // Show tab corresponding to the hash
  let tab = window.location.hash;
  if (tab) {
    let $tab = $("#" + idPrefix + tab.substring(1) + idSuffix);
    if ($tab.length) {
      $tab.tab("show");
    }
  }

  // Set hash when tab clicked
  $('a[data-toggle="tab"]').on("shown.bs.tab", function (e) {
    let id = $(e.target).attr("id");
    window.location.hash = id.substring(idPrefix.length, id.indexOf(idSuffix));
    return false;
  })
})();
