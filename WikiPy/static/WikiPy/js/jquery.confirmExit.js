(function () {
  window.__confirmExitCounter = 0;

  $.fn.confirmExit = function () {
    this._confirmExit = false;
    this._savedState = this.serialize();

    /**
     * Disables the form confirmation. If the global counter is 0,
     * the onbeforeunload event is set to null.
     */
    let disable = () => {
      if (this._confirmExit) {
        this._confirmExit = false;
        __confirmExitCounter--;
        if (__confirmExitCounter === 0) {
          window.onbeforeunload = null;
        }
      }
    };

    $("input, textarea, select", this).on("change keyup", () => {
      if (this.serialize() !== this._savedState) {
        // Do not set the event handler if not needed
        if (!this._confirmExit) {
          this._confirmExit = true;
          __confirmExitCounter++;

          window.onbeforeunload = function (e) {
            // For old IE and Firefox
            if (e) {
              e.returnValue = true;
            }
            return true;
          }
        }
        // Disable if already set but form is back to initial state
      } else if (this._confirmExit) {
        disable();
      }
    });

    this.submit(disable);

    return this;
  }
})();
