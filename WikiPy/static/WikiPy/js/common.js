"use strict";

(function () {
  if (!Array.prototype.remove) {
    Array.prototype.remove = function (value) {
      let index = this.indexOf(value);
      if (index > -1) {
        this.splice(index, 1);
      }
    };
  }

  let WPY_CONF = {};
  // noinspection JSUnresolvedVariable
  for (let [k, v] of Object.entries(window.WPY_CONF || {})) {
    WPY_CONF[k] = v;
  }
  // noinspection JSUnresolvedVariable
  delete window.WPY_CONF;

  class LockableMap {
    _values;
    _immutable;

    constructor(immutable) {
      this._values = {};
      this._immutable = !!immutable;
    }

    setImmutable() {
      this._immutable = true;
    }

    get(key, fallback) {
      return this._values[key] || fallback;
    }

    set(key, value) {
      if (this._immutable) {
        throw new Error("Map object is immutable");
      }
      this._values[key] = value;
    }

    [Symbol.iterator]() {
      return this.entries();
    }

    * entries() {
      for (let [k, v] of Object.entries(this._values)) {
        yield [k, v];
      }
    }

    * keys() {
      for (let k of Object.keys(this._values)) {
        yield k;
      }
    }

    * values() {
      for (let v of Object.values(this._values)) {
        yield v;
      }
    }
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

  window.wpy = {
    Map: LockableMap,

    config: config,

    modules: {},

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
     * If no mapping correspond to the given key, the key is returned.
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
     * @param moduleName {string} The module’s name. Must follow the format "[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*".
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
      let names = moduleName.split('.');
      let obj = this.modules;
      // Build modules "namespaces"
      for (let i = 0, last = false; i < names.length; i++, last = i === names.length - 1) {
        let name = names[i];
        if (!obj.hasOwnProperty(name)) {
          if (last) {
            obj[name] = module;
          } else {
            obj = obj[name] = {};
          }
        } else {
          obj = obj[name];
        }
      }
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
     * Returns the module for the given name.
     * @param name {string} The module’s name.
     * @return {object|undefined} The module or undefined in none correspond.
     */
    getModule: function (name) {
      return this._modules[name];
    },

    /**
     * Tells whether the given module has been loaded.
     * @param name {string} The module’s name.
     * @return {boolean} True if it is loaded, false otherwise.
     */
    isModuleLoaded: function (name) {
      return !!this.getModule(name);
    },

    currentPage: {
      getTitle: function (url) {
        let key = "PageTitle";
        if (url) {
          key = "Url" + key;
        }
        return WPY_CONF["wpy" + key];
      },

      getSpecialPageTitle: function (url, canonical) {
        let key = "SpecialPageTitle";
        if (canonical) {
          key = "Canonical" + key;
        }
        if (url) {
          key = "Url" + key;
        }
        console.log(key);
        return WPY_CONF["wpy" + key];
      },

      getFullTitle: function (url) {
        let key = "FullPageTitle";
        if (url) {
          key = "Url" + key;
        }
        return WPY_CONF["wpy" + key];
      },

      getNamespaceName: function (url, canonical) {
        let key = "NamespaceName";
        if (canonical) {
          key = "Canonical" + key;
        }
        if (url) {
          key = "Url" + key;
        }
        return WPY_CONF["wpy" + key];
      },

      getNamespaceId: function () {
        return WPY_CONF["wpyNamespaceId"];
      },

      getAction: function () {
        return WPY_CONF["wpyAction"];
      },

      getContentType: function () {
        return WPY_CONF["wpyContentType"];
      },

      getSkin: function () {
        return WPY_CONF["wpySkin"];
      },
    },

    currentUser: {
      getName: function () {
        return WPY_CONF["wpyUserName"];
      },

      getId: function () {
        return WPY_CONF["wpyUserId"];
      },

      isLoggedIn: function () {
        return WPY_CONF["wpyUserIsLoggedIn"];
      },

      getGroups: function () {
        return WPY_CONF["wpyUserGroups"];
      },
    },

    toast: {
      /**
       *
       * @param title {string} Toast’s title.
       * @param message {string} Toast’s message.
       * @param autoHide {boolean} True to hide automatically after the specified delay.
       * @param hideDelay {number?} If autoHide is true, the delay in seconds (integer) until the toat disappears.
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
  let accessKeyLabel = 'alt+shift+';

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

  function updatePageLayout() {
    if (window.innerWidth <= 1224) {
      $("#wpy-nav-bar-right").insertAfter($("#wpy-nav-bar-left"));
    } else {
      $("#wpy-center-col").next().append($("#wpy-nav-bar-right"));
    }
  }

  updatePageLayout();
  $(window).resize(updatePageLayout);
})();
