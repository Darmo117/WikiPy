"use strict";

(function () {
  let $options = $("#wpy-search-form-namespaces > option");

  function callbackFactory(nsIds) {
    return e => {
      $options.each((_, option) => {
        let $option = $(option);
        let ns = nsIds.includes(parseInt($option.val()));
        if (ns) {
          $option.prop("selected", e.target.checked);
        }
      });
    }
  }

  // TODO select default ns if no ns specified
  $("#wpy-search-form-default-ns").click(callbackFactory([0])); // Main
  $("#wpy-search-form-help-ns").click(callbackFactory([-2, 6])); // WikiNamespace, Help
  $("#wpy-search-form-all-ns").click(callbackFactory(Object.values(wpy.config.get("wpyNamespacesIds"))));
})();
