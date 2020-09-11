(function () {
  "use strict";

  let requestedNs = $("#wpy-search-form-query-namespaces").val().split(',');
  let namespaces = Object.entries(wpy.config.get("wpyNamespaces"));

  for (let [nsId, nsName] of namespaces) {
    if (nsId !== "-1") {
      if (nsId === "0") {
        nsName = `(${wpy.config.get("wpyMainNamespaceName")})`;
      }
      let $option = $(`<option value="${nsId}">${nsName}</option>`);
      $("#wpy-search-form-namespaces").append($option);
      $option.prop("selected", requestedNs.includes(nsId))
    }
  }

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

  $("#wpy-search-form-defaultns").click(callbackFactory([0]));
  $("#wpy-search-form-talkns").click(callbackFactory(wpy.config.get("wpyTalkNamespaces")));
  $("#wpy-search-form-helpns").click(callbackFactory([-3, 12]));
  $("#wpy-search-form-allns").click(callbackFactory(Object.values(wpy.config.get("wpyNamespacesIds"))));
})();
