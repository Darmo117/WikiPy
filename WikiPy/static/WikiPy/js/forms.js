(function () {
  // Add .is-invalid class to form inputs with associated
  // .invalid-feedback div.
  $("form div.form-group").each(function () {
    let $e = $(this);
    if ($e.find("div.invalid-feedback").length) {
      $e.find("input, select").addClass("is-invalid");
    }
  });

  /*
   * Handle password confirmation.
   */
  $("form").each(function () {
    let $form = $(this);
    let formId = $form.attr("id");
    let $passwordConfirmation = $(`#${formId}-password-confirm`);

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

    // Store form state at page load
    $form.initial_form_state = $form.serialize();

    // Store form state after form submit
    $form.submit(function () {
      $form.initial_form_state = $form.serialize();
    });

    if ($form.find('input[name="warn-unsaved"]').length) {
      // Check form changes before leaving the page and warn user if needed
      $(window).bind("beforeunload", function (e) {
        let form_state = $form.serialize();
        if ($form.initial_form_state !== form_state) {
          let message = "You have unsaved changes on this page. Do you want to leave this page and discard your changes or stay on this page?";
          e.returnValue = message; // Cross-browser compatibility (src: MDN)
          return message;
        }
      });
    }
  });
})();
