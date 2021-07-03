(function () {
  "use strict";

  let $newTopicForm = $("#wpy-new-topic-form");
  $("#wpy-new-topic-btn").click(function () {
    $newTopicForm.show();
    $newTopicForm.trigger("reset");
    // For ACE editor
    $("#wpy-new-topic-form-content").change();
  });
  $("#wpy-new-topic-form-cancel-btn").click(function () {
    $newTopicForm.trigger("reset");
    // For ACE editor
    $("#wpy-new-topic-form-content").change();
    $newTopicForm.hide();
  });
  $newTopicForm.submit(function () {
    // TODO send AJAX POST
    return false; // Prevent page reloading
  });

  let $editMessageForm = $("#wpy-edit-message-form");
  $(".wpy-reply-btn").click(function () {
    // TODO move form below the message being replied to and retrieve its ID
    $editMessageForm.show();
    $editMessageForm.trigger("reset");
    // For ACE editor
    $("#wpy-edit-message-form-content").change();
  });
  $("#wpy-edit-message-form-cancel-btn").click(function () {
    $editMessageForm.trigger("reset");
    // For ACE editor
    $("#wpy-edit-message-form-content").change();
    $editMessageForm.hide();
  });
  $editMessageForm.submit(function () {
    // TODO send AJAX POST
    return false; // Prevent page reloading
  });
})();
