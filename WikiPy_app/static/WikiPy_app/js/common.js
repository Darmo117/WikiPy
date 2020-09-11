(function () {
  "use strict";

  let WPY_CONF = {};
  for (let [k, v] of Object.entries(window.WPY_CONF || {})) {
    WPY_CONF[k] = v;
  }
  window.WPY_CONF = undefined; // Delete global variable

  class Map {
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

  let config = new Map();
  for (let [k, v] of Object.entries(WPY_CONF)) {
    if (!k.endsWith("PageTitle") &&
        !k.endsWith("NamespaceName") &&
        !k.endsWith("NamespaceId") &&
        !k.startsWith("wpyUser") &&
        !["wpyAction", "wpyContentType", "wpySkin"].includes(k) ||
        k === "wpyMainNamespaceName") {
      config.set(k, v);
    }
  }
  config.setImmutable();

  window.wpy = {
    Map: Map,
    config: config,
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
  };

  /* Add keystroke in tooltips of elements with accesskey attribute. */
  (function () {
    let accessKeyLabel = 'alt+shift+';

    $("*[accesskey]").each(function (_, e) {
      let $element = $(e);
      let tooltip = $element.attr("title");
      let accessKey = $element.attr("accesskey");

      if (tooltip) {
        $element.attr("title", $element.attr("title") + ` [${accessKeyLabel + accessKey}]`);
      }
    });
  })();
})();
