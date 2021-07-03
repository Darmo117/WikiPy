/**
 * This module sets up the ACE editor if activated by the user.
 * The editor needs a div element with the following attributes:
 * - class containing "wpy-ace-editor"
 * - data-ace-target referencing the id of the textarea to wrap
 * - id="<target id>-ace"
 * - data-content-model holding the content model of the text inside the wrapped textarea
 * <br>
 * To put the editor in readonly mode, add data-disabled="1" to the div element.
 *
 * @author Damien Vergnet
 */
(function () {
  "use strict";

  if (ace) { // User may have disabled it.
    wpy.registerModule("core.ace_editor", function () {
      let editors = {};

      $("div.wpy-ace-editor").each(function () {
        let $div = $(this);
        let contentModel = $div.data("content-model");
        let disabled = !!$div.data("disabled");
        let targetId = $div.data("ace-target");
        let $textarea = $("#" + targetId).hide();
        let editor = ace.edit(targetId + "-ace", {
          mode: "ace/mode/" + (contentModel === "module" ? "python" : contentModel),
          useSoftTabs: true,
          fontSize: 16,
          minLines: 20,
          maxLines: 20,
        });
        editor.getSession().setValue($textarea.val());
        editor.getSession().on("change", function () {
          // Update form textarea on each change in the editor
          $textarea.val(editor.getSession().getValue());
        });
        $textarea.on("change", function () {
          editor.getSession().setValue($textarea.val());
        });

        if (disabled) {
          editor.setReadOnly(true);
        }

        editors[targetId] = editor;
      });

      return {
        editors: editors,
      };
    });
  }
})();
