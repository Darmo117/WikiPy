"use strict";

(function () {
  function updateDateFieldsDisabledState() {
    let disable = $(this).val() === 'all';
    $("#wpy-protect-page-form-predefined-expiration-date").prop('disabled', disable);
    $("#wpy-protect-page-form-expiration-date").prop('disabled', disable);
  }

  function updateCustomDateFieldDisabledState() {
    let disable = $(this).val() !== 'other';
    $("#wpy-protect-page-form-expiration-date").prop('disabled', disable);
  }

  let $select1 = $("#wpy-protect-page-form-level");
  updateDateFieldsDisabledState.call($select1);
  $select1.on('change', updateDateFieldsDisabledState);
  // noinspection JSJQueryEfficiency
  let $select2 = $("#wpy-protect-page-form-predefined-expiration-date");
  updateCustomDateFieldDisabledState.call($select2);
  $select2.on('change', updateCustomDateFieldDisabledState);
})();
