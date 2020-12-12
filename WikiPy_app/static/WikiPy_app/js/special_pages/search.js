"use strict";

(function () {
  $("#wpy-search-form-namespaces > option[value='0']").text(`(${wpy.config.get("wpyMainNamespaceName")})`);

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

  $("#wpy-search-form-default-ns").click(callbackFactory([0]));
  $("#wpy-search-form-talk-ns").click(callbackFactory(wpy.config.get("wpyTalkNamespaces")));
  $("#wpy-search-form-help-ns").click(callbackFactory([-3, 12]));
  $("#wpy-search-form-all-ns").click(callbackFactory(Object.values(wpy.config.get("wpyNamespacesIds"))));
})();
