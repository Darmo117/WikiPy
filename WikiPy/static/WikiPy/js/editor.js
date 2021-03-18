"use strict";

(function () {
  if (ace) { // User may have disabled it.
    wpy.registerModule("core.ace_editor", function () {
      let contentModel = wpy.config.get("wpyContentModel");
      let $textarea = $("#wpy-edit-form-content").hide();
      let editor = ace.edit("wpy-ace-editor", {
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

      if ($("#wpy-editor-disabled").length) {
        editor.setReadOnly(true);
      }

      return editor;
    });
  }
})();
