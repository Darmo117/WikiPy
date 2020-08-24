$(function () {
  "use strict";

  let requestedNs = $("#wpy-contribs-form-selectednamespace").val();
  let namespaces = Object.entries(wpy.config.get("wpyNamespaces"));
  namespaces.unshift(["*", "All"]);

  for (let [nsId, nsName] of namespaces) {
    if (nsId === "0") {
      nsName = `(${wpy.config.get("wpyMainNamespaceName")})`;
    }
    let selected = requestedNs === nsId;
    let $option = $(`<option value="${nsId}">${nsName}</option>`);
    $("#wpy-contribs-form-namespace").append($option);
    $option.prop("selected", selected)
  }

  $("#wpy-contribs-form").submit(function () {
    let username = $("#wpy-contribs-form-targetuser").val();
    let fields = $("#wpy-contribs-form input[name!=target_user][type!=submit][type!=hidden], #wpy-contribs-form select");
    let params = [];

    for (let field of fields) {
      let $field = $(field);
      let value = "";

      if ($field.attr("type") === "checkbox") {
        value = $field.prop("checked") ? 1 : 0;
      }
      else {
        value = $field.val();
      }
      if (value && !($field.attr("name") === "namespace" && value === "*")) {
        params.push(`${$field.attr("name")}=${value}`);
      }
    }

    let url = wpy.config.get("wpyUrlPath") + wpy.config.get("wpyNamespaces")[-1] + ":" +
        wpy.currentPage.getSpecialPageTitle(true) + "/" + username;
    if (params.length) {
      url += "?" + params.join("&");
    }
    location.href = url;
    return false;
  })
});
