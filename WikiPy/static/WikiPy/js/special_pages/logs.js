"use strict";

(function () {
  function update() {
    let disable = $(this).val() === 'user_creation';
    $("#wpy-logs-form-target").prop('disabled', disable);
  }

  let $select = $("#wpy-logs-form-type");
  update.call($select);
  $select.on('change', update);
})();
