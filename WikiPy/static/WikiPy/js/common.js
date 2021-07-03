/**
 * This file initializes the wpy global object.
 *
 * @author Damien Vergnet
 */
(function () {
  "use strict";

  // Add in-place remove method to arrays.
  Array.prototype.remove = function (value) {
    let index = this.indexOf(value);
    if (index > -1) {
      this.splice(index, 1);
    }
  };

  let WPY_CONF = {};
  // noinspection JSUnresolvedVariable
  for (let [k, v] of Object.entries(window.WPY_CONF || {})) {
    WPY_CONF[k] = v;
  }
  // noinspection JSUnresolvedVariable
  delete window.WPY_CONF;

  /**
   * A simple map object that can be locked but never unlocked.
   *
   * @author Damien Vergnet
   */
  class LockableMap extends Map {
    /**
     * Creates a new, unlocked map.
     */
    constructor() {
      super();
      this._immutable = false;
    }

    /**
     * Renders this map immutable.
     */
    setImmutable() {
      this._immutable = true;
    }

    /**
     * Sets a value for the given key.
     * @param key {string} The key.
     * @param value {*} The associated value.
     * @throws Error If this map is locked.
     */
    set(key, value) {
      if (this._immutable) {
        throw new Error("Map object is immutable");
      }
      super.set(key, value);
    }

    /** @private */
    _immutable;
  }

  let config = new LockableMap();
  for (let [k, v] of Object.entries(WPY_CONF)) {
    if (!k.endsWith("PageTitle") &&
        !k.endsWith("NamespaceName") &&
        !k.endsWith("NamespaceId") &&
        !k.startsWith("wpyUser") &&
        k !== "wpyTranslations" &&
        !["wpyAction", "wpyContentType", "wpySkin"].includes(k) ||
        k === "wpyMainNamespaceName") {
      config.set(k, v);
    }
  }
  config.setImmutable();

  /**
   * The "wpy" object contains all methods and attributes of the WikiPy JavaScript API.
   *
   * @author Damien Vergnet
   */
  window.wpy = {
    /**
     * A simple map object that can be locked but never unlocked.
     * @see LockableMap
     */
    LockableMap: LockableMap,

    /**
     * The config attribute contains global wiki data along with some related to the current page.
     */
    config: config,

    /**
     * Encodes a string into a valid wiki page title URL.
     * @param s {string} The string to encode.
     * @return {string} The encoded string.
     */
    encodePageTitleUrl: function (s) {
      return s.replaceAll(" ", "_").replaceAll("?", "%3F");
    },

    /**
     * Returns the translation for the given key.
     * If there is no mapping for the given key, the key is returned.
     * @param key {string}
     * @param args {Object?}
     * @return {string}
     */
    translate: function (key, args) {
      let string = WPY_CONF["wpyTranslations"][key] || key;
      for (let [k, v] of Object.entries(args || {})) {
        string = string.replace(`\${${k}}`, `${v}`);
      }
      return string;
    },

    /**
     * Registers a callback to be called once all
     * modules in the given dependencies list have been loaded.
     * If all dependencies have already been loaded, the callback is
     * called immediately.
     * @param dependencies {Array<string>|string} The list of dependencies.
     * @param callback {Function} The function to call.
     */
    when: function (dependencies, callback) {
      if (typeof dependencies === "string") {
        dependencies = [dependencies];
      } else if (!(dependencies instanceof Array)) {
        throw new TypeError("dependencies must be a string or array of strings");
      }
      if (typeof callback !== "function") {
        throw new TypeError("callback must be callable");
      }

      let toRemove = [];
      for (let d of dependencies) {
        if (this.getModule(d)) {
          toRemove.push(d);
        }
      }
      toRemove.forEach(d => dependencies.remove(d));

      if (!dependencies.length) {
        // All dependencies have already been loaded, call the function now
        callback();
      } else {
        this._eventsQueue.set(callback, dependencies);
      }
    },

    /**
     * Registers a module for the given name. A property "id" holding the name of the module is added
     * to the object returned by the function.
     * Once registered, the module can be accessed by calling <code>wpy.getModule("<module id>")</code>.
     * @param moduleName {string} The module’s name. Must follow the format <code>[a-zA-Z0-9\_]+(\.[a-zA-Z0-9_]+)*</code>.
     * @param f {Function} The callback function that will load the module. It must return an object.
     */
    registerModule: function (moduleName, f) {
      if (!/^\w+(\.\w+)*$/.exec(moduleName)) {
        console.error(`Invalid module name "${moduleName}", skipped.`);
        return;
      }
      if (this.getModule(moduleName)) {
        console.error(`A module with the name "${moduleName}" is already registered, skipped.`);
        return;
      }

      let module = f();
      module.id = moduleName;
      this._modules[moduleName] = module;

      let toRemove = [];
      for (let [callback, dependencies] of this._eventsQueue) {
        if (dependencies.includes(moduleName)) {
          dependencies.remove(moduleName);
          if (!dependencies.length) {
            callback();
            toRemove.push(callback);
          }
        }
      }
      toRemove.forEach(d => this._eventsQueue.delete(d));
    },

    /**
     * Returns the module for the given ID.
     * @param id {string} The module’s ID.
     * @return {object|undefined} The module or undefined in none correspond.
     */
    getModule: function (id) {
      return this._modules[id];
    },

    /**
     * Tells whether the given module has been loaded.
     * @param id {string} The module’s ID.
     * @return {boolean} True if it is loaded, false otherwise.
     */
    isModuleLoaded: function (id) {
      return !!this.getModule(id);
    },

    /**
     * This attribute defines methods related to the current page.
     */
    currentPage: {
      /**
       * Returns the title (without the namespace) of the current page.
       * @param asUrl {boolean} If true, the returned title will be URL-compatible.
       * @return {string} The current page’s title.
       */
      getTitle: function (asUrl) {
        let key = "PageTitle";
        if (asUrl) {
          key = "Url" + key;
        }
        return WPY_CONF["wpy" + key];
      },

      /**
       * Returns the title (without the namespace) of the current special page.
       * @param asUrl {boolean} If true, the returned title will be URL-compatible.
       * @param canonical {boolean} If true, the canonical title is returned; otherwise the local one is.
       * @return {string} The current special page’s title.
       */
      getSpecialPageTitle: function (asUrl, canonical) {
        let key = "SpecialPageTitle";
        if (canonical) {
          key = "Canonical" + key;
        }
        if (asUrl) {
          key = "Url" + key;
        }
        return WPY_CONF["wpy" + key];
      },

      /**
       * Returns the title (with the namespace) of the current page.
       * @param asUrl {boolean} If true, the returned title will be URL-compatible.
       * @return {string} The current page’s title.
       */
      getFullTitle: function (asUrl) {
        let key = "FullPageTitle";
        if (asUrl) {
          key = "Url" + key;
        }
        return WPY_CONF["wpy" + key];
      },

      /**
       * Returns the namespace name of the current page.
       * @param asUrl {boolean} If true, the returned namespace will be URL-compatible.
       * @param canonical {boolean} If true, the canonical namespace name is returned; otherwise the local one is.
       * @return {string} The current page’s namespace name.
       */
      getNamespaceName: function (asUrl, canonical) {
        let key = "NamespaceName";
        if (canonical) {
          key = "Canonical" + key;
        }
        if (asUrl) {
          key = "Url" + key;
        }
        return WPY_CONF["wpy" + key];
      },

      /**
       * Returns the namespace ID of the current page.
       * @return {number} The namespace ID of the current page.
       */
      getNamespaceId: function () {
        return WPY_CONF["wpyNamespaceId"];
      },

      /**
       * Returns the action of the current page.
       * @return {string} The action of the current page.
       */
      getAction: function () {
        return WPY_CONF["wpyAction"];
      },

      /**
       * Returns the content type of the current page.
       * @return {string} The content type of the current page.
       */
      getContentType: function () {
        return WPY_CONF["wpyContentType"];
      },

      /**
       * Returns the ID of the currently used skin.
       * @return {*} The ID of the current skin.
       */
      getSkin: function () {
        return WPY_CONF["wpySkin"];
      },
    },

    /**
     * This attribute defines methods related to the current user.
     */
    currentUser: {
      /**
       * Returns the name of the current user.
       * @return {string} The name of the current user.
       */
      getName: function () {
        return WPY_CONF["wpyUserName"];
      },

      /**
       * Returns the ID of the current user.
       * @return {number} The ID of the current user.
       */
      getId: function () {
        return WPY_CONF["wpyUserId"];
      },

      /**
       * Tells whether the current user is logged in.
       * @return {boolean} True if the current user is logged in; false otherwise.
       */
      isLoggedIn: function () {
        return WPY_CONF["wpyUserIsLoggedIn"];
      },

      /**
       * Returns the groups of the current user.
       * @return {Array<string>} The groups of the current user.
       */
      getGroups: function () {
        return WPY_CONF["wpyUserGroups"];
      },
    },

    /**
     * This attribute defines methods related toast popups.
     */
    toast: {
      /**
       * Displays a toast popup.
       * @param title {string} Toast’s title.
       * @param message {string} Toast’s message.
       * @param autoHide {boolean} True to hide automatically after the specified delay.
       * @param hideDelay {number?} If autoHide is true, the delay in seconds (integer) until the toast disappears.
       * Defaults to 0.
       */
      show: function (title, message, autoHide, hideDelay) {
        autoHide = !!autoHide;
        hideDelay = Math.floor(hideDelay || 0);
        let closeTooltip = wpy.translate("toast.close.tooltip");
        let $toast = $(`
          <div class="toast" role="alert" aria-live="assertive" aria-atomic="true"
              data-delay="${hideDelay * 1000}" data-autohide="${autoHide}">
            <div class="toast-header">
              <strong class="mr-auto">${title}</strong>
              <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="${closeTooltip}"
                  title="${closeTooltip}">
                <span aria-hidden="true">×</span>
              </button>
            </div>
            <div class="toast-body">${message}</div>
          </div>
        `.trim());
        $("#wpy-toasts-area").append($toast);
        $toast.toast("show");
        // Delete toats once it is completely hidden.
        $toast.on("hidden.bs.toast", function () {
          $toast.remove();
        })
      }
    },

    /** @private */
    _modules: {},
    /** @private */
    _eventsQueue: new Map(),
  };

  /* Add keystroke in tooltips of elements with accesskey attribute. */
  let accessKeyLabel = "alt+shift+";
  $("*[accesskey]").each(function (_, e) {
    let $element = $(e);
    let tooltip = $element.attr("title");
    let accessKey = $element.attr("accesskey");

    if (tooltip) {
      $element.attr("title", $element.attr("title") + ` [${accessKeyLabel + accessKey}]`);
    }
  });

  function addLanguageParam(url, value) {
    let params = new URLSearchParams(url.search);
    params.set("use_lang", value);
    url.search = params.toString();
  }

  // Language selector behavior.
  let $languageSelector = $("#wpy-language-select");
  if ($languageSelector.length) {
    // Select current language
    $languageSelector.val(wpy.config.get("wpyLanguageCode"));

    // Language select handler
    $languageSelector.change(function () {
      let language = $(this).val();
      let url = new URL(location.href);
      addLanguageParam(url, language);
      location.href = url.toString();
    });

    let language = new URL(location.href).searchParams.get("use_lang");

    if (language) {
      // Add use_lang parameter to all internal links that are not dropdown toggles
      $("a:not([data-toggle])").each(function () {
        let $anchor = $(this);
        let href = $anchor.prop("href");

        if (href) {
          let url = new URL(href);
          if (url.hostname === location.hostname) {
            addLanguageParam(url, language);
            $anchor.prop("href", url.toString());
          }
        }
      });
    }
  }

  // Email confirmation resend button
  $("#wpy-change-email-resend").click(function () {
    $.get(
        wpy.config.get("wpyApiUrlPath"),
        {
          "action": "send_confirmation_email",
          "format": "json",
        },
        function (data) {
          if (data["sent"]) {
            wpy.toast.show(wpy.translate("toast.email_sent.title"), wpy.translate("toast.email_sent.message"), true, 5)
          }
        }
    );
    return false;
  });
})();
