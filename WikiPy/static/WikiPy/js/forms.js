/**
 * This file handles various things related to forms:
 * - Password confirmation if needeed
 * - Invalid data CSS classes
 * - Unsaved changes warnings
 *
 * @author Damien Vergnet
 */
(function () {
  // Add .is-invalid class to form inputs with associated
  // .invalid-feedback div.
  $("form div.form-group").each(function () {
    let $e = $(this);
    if ($e.find("div.invalid-feedback").length) {
      $e.find("input, select").addClass("is-invalid");
    }
  });

  // Iterate over all forms
  $("form").each(function () {
    let $form = $(this);
    let formId = $form.attr("id");
    let $passwordConfirmation = $(`#${formId}-password-confirm`);

    /*
     * Handle password confirmation.
     */
    if ($passwordConfirmation.length) {
      let $password = $(`#${formId}-password`);
      let $submit = $(`#${formId}-submit`);
      $submit.prop("disabled", true);

      function checkPasswords() {
        let password1 = $password.val();
        let password2 = $passwordConfirmation.val();

        if ((!password1 && !password2) || password1 !== password2) {
          $password.addClass("is-invalid");
          $passwordConfirmation.addClass("is-invalid");
          $submit.prop("disabled", true);
        } else {
          $password.removeClass("is-invalid");
          $passwordConfirmation.removeClass("is-invalid");
          $submit.prop("disabled", false);
        }
      }

      $password.keyup(checkPasswords);
      $passwordConfirmation.keyup(checkPasswords);
    }

    // Handle unsaved warning.
    if ($form.find('input[name="warn-unsaved"]').length) {
      $form.confirmExit();
    }

    // Cancel button of page edit form.
    if (formId === "wpy-edit-form") {
      $("#wpy-edit-form-cancel-btn").click(function () {
        // Remove onbeforeunload event if it was set by confirmExit.
        window.onbeforeunload = null;
        history.back();
      });
    }
  });
})();
