function isCompatible(ua) {
  return !!((function () {
    'use strict';
    return !this && Function.prototype.bind && window.JSON;
  }()) && 'querySelector' in document && 'localStorage' in window && 'addEventListener' in window && !ua.match(/MSIE 10|NetFront|Opera Mini|S40OviBrowser|MeeGo|Android.+Glass|^Mozilla\/5\.0 .+ Gecko\/$|googleweblight|PLAYSTATION|PlayStation/));
}

if (!isCompatible(navigator.userAgent)) {
  document.documentElement.className = document.documentElement.className.replace(/(^|\s)client-js(\s|$)/, '$1client-nojs$2');
  while (window.NORLQ && NORLQ[0]) {
    NORLQ.shift()();
  }
  NORLQ = {
    push: function (fn) {
      fn();
    }
  };
  RLQ = {
    push: function () {
    }
  };
}
else {
  if (window.performance && performance.mark) {
    performance.mark('mwStartup');
  }
  (function () {
    'use strict';
    var mw, StringSet, log, hasOwn = Object.hasOwnProperty,
        console = window.console;

    function fnv132(str) {
      var hash = 0x811C9DC5,
          i = 0;
      for (; i < str.length; i++) {
        hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
        hash ^= str.charCodeAt(i);
      }
      hash = (hash >>> 0).toString(36).slice(0, 5);
      while (hash.length < 5) {
        hash =
            '0' + hash;
      }
      return hash;
    }

    function defineFallbacks() {
      StringSet = window.Set || function () {
        var set = Object.create(null);
        return {
          add: function (value) {
            set[value] = !0;
          },
          has: function (value) {
            return value in set;
          }
        };
      };
    }

    function setGlobalMapValue(map, key, value) {
      map.values[key] = value;
      log.deprecate(window, key, value, map === mw.config && 'Use mw.config instead.');
    }

    function logError(topic, data) {
      var msg, e = data.exception;
      if (console && console.log) {
        msg = (e ? 'Exception' : 'Error') + ' in ' + data.source + (data.module ? ' in module ' + data.module : '') + (e ? ':' : '.');
        console.log(msg);
        if (e && console.warn) {
          console.warn(e);
        }
      }
    }

    function Map(global) {
      this.values = Object.create(null);
      if (global === true) {
        this.set = function (selection, value) {
          var s;
          if (arguments.length > 1) {
            if (typeof selection === 'string') {
              setGlobalMapValue(this, selection, value);
              return true;
            }
          }
          else if (typeof selection === 'object') {
            for (s in selection) {
              setGlobalMapValue(this, s, selection[s]);
            }
            return true;
          }
          return false;
        };
      }
    }

    Map.prototype = {
      constructor: Map,
      get: function (selection, fallback) {
        var
            results, i;
        fallback = arguments.length > 1 ? fallback : null;
        if (Array.isArray(selection)) {
          results = {};
          for (i = 0; i < selection.length; i++) {
            if (typeof selection[i] === 'string') {
              results[selection[i]] = selection[i] in this.values ? this.values[selection[i]] : fallback;
            }
          }
          return results;
        }
        if (typeof selection === 'string') {
          return selection in this.values ? this.values[selection] : fallback;
        }
        if (selection === undefined) {
          results = {};
          for (i in this.values) {
            results[i] = this.values[i];
          }
          return results;
        }
        return fallback;
      },
      set: function (selection, value) {
        var s;
        if (arguments.length > 1) {
          if (typeof selection === 'string') {
            this.values[selection] = value;
            return true;
          }
        }
        else if (typeof selection === 'object') {
          for (s in selection) {
            this.values[s] = selection[s];
          }
          return true;
        }
        return false;
      },
      exists: function (selection) {
        return typeof selection === 'string' && selection in this.values;
      }
    };
    defineFallbacks();
    log = function () {
    };
    log.warn = console && console.warn ? Function.prototype.bind.call(console.warn, console) : function () {
    };
    log.error = console && console.error ? Function.prototype.bind.call(console.error, console) : function () {
    };
    log.deprecate = function (obj, key, val, msg, logName) {
      var stacks;

      function maybeLog() {
        var name = logName || key,
            trace = new Error().stack;
        if (!stacks) {
          stacks = new StringSet();
        }
        if (!stacks.has(trace)) {
          stacks.add(trace);
          if (logName || obj === window) {
            mw.track('mw.deprecate', name);
          }
          mw.log.warn('Use of "' + name + '" is deprecated.' + (msg ? ' ' + msg : ''));
        }
      }

      try {
        Object.defineProperty(obj, key, {
          configurable: !0,
          enumerable: !0,
          get: function () {
            maybeLog();
            return val;
          },
          set: function (newVal) {
            maybeLog();
            val = newVal;
          }
        });
      }
      catch (err) {
        obj[key] = val;
      }
    };
    mw = {
      redefineFallbacksForTest: window.QUnit && defineFallbacks,
      now: function () {
        var perf = window.performance,
            navStart = perf && perf.timing && perf.timing.navigationStart;
        mw.now = navStart && perf.now ? function () {
          return navStart + perf.now();
        } : Date.now;
        return mw.now();
      },
      trackQueue: [],
      track: function (topic, data) {
        mw.trackQueue.push({
          topic: topic,
          data: data
        });
      },
      trackError: function (topic, data) {
        mw.track(topic, data);
        logError(topic, data);
      },
      Map: Map,
      config: new Map(true),
      messages: new Map(),
      templates: new Map(),
      log: log,
      loader: (function () {
        var registry = Object.create(null),
            sources = Object.create(null),
            handlingPendingRequests = !1,
            pendingRequests = [],
            queue = [],
            jobs = [],
            willPropagate = !1,
            errorModules = [],
            baseModules = ["jquery", "mediawiki.base"],
            marker = document.querySelector('meta[name="ResourceLoaderDynamicStyles"]'),
            lastCssBuffer, rAF = window.requestAnimationFrame || setTimeout;

        function newStyleTag(text, nextNode) {
          var el = document.createElement('style');
          el.appendChild(document.createTextNode(text));
          if (nextNode && nextNode.parentNode) {
            nextNode.parentNode.insertBefore(el, nextNode);
          }
          else {
            document.head.appendChild(el);
          }
          return el;
        }

        function flushCssBuffer(cssBuffer) {
          var i;
          if (cssBuffer === lastCssBuffer) {
            lastCssBuffer = null;
          }
          newStyleTag(cssBuffer.cssText, marker);
          for (i = 0; i < cssBuffer.callbacks.length; i++) {
            cssBuffer.callbacks[i]();
          }
        }

        function addEmbeddedCSS(cssText, callback) {
          if (!lastCssBuffer || cssText.slice(0, '@import'.length) === '@import') {
            lastCssBuffer = {
              cssText: '',
              callbacks: []
            };
            rAF
            (flushCssBuffer.bind(null, lastCssBuffer));
          }
          lastCssBuffer.cssText += '\n' + cssText;
          lastCssBuffer.callbacks.push(callback);
        }

        function getCombinedVersion(modules) {
          var hashes = modules.reduce(function (result, module) {
            return result + registry[module].version;
          }, '');
          return fnv132(hashes);
        }

        function allReady(modules) {
          var i = 0;
          for (; i < modules.length; i++) {
            if (mw.loader.getState(modules[i]) !== 'ready') {
              return false;
            }
          }
          return true;
        }

        function allWithImplicitReady(module) {
          return allReady(registry[module].dependencies) && (baseModules.indexOf(module) !== -1 || allReady(baseModules));
        }

        function anyFailed(modules) {
          var state, i = 0;
          for (; i < modules.length; i++) {
            state = mw.loader.getState(modules[i]);
            if (state === 'error' || state === 'missing') {
              return true;
            }
          }
          return false;
        }

        function doPropagation() {
          var errorModule, baseModuleError, module, i, failed, job, didPropagate = !0;
          do {
            didPropagate = !1;
            while (errorModules.length) {
              errorModule = errorModules.shift();
              baseModuleError = baseModules.indexOf(errorModule) !== -1;
              for (module in registry) {
                if (registry[module].state !== 'error' && registry[module].state !== 'missing') {
                  if (baseModuleError && baseModules.indexOf(module) === -1) {
                    registry[module].state = 'error';
                    didPropagate = !0;
                  }
                  else if (registry[module].dependencies.indexOf(errorModule) !== -1) {
                    registry[module].state = 'error';
                    errorModules.push(module);
                    didPropagate = !0;
                  }
                }
              }
            }
            for (module in registry) {
              if (registry[module].state === 'loaded' && allWithImplicitReady(module)) {
                execute(module);
                didPropagate = !0;
              }
            }
            for (i = 0; i < jobs.length; i++) {
              job = jobs[i];
              failed = anyFailed(job.dependencies);
              if (failed || allReady(job.dependencies)) {
                jobs.splice(i, 1);
                i -= 1;
                try {
                  if (failed && job.error) {
                    job.error(new Error('Failed dependencies'), job.dependencies);
                  }
                  else if (!failed && job.ready) {
                    job.ready();
                  }
                }
                catch (e) {
                  mw.trackError('resourceloader.exception', {
                    exception: e,
                    source: 'load-callback'
                  });
                }
                didPropagate = !0;
              }
            }
          } while (didPropagate);
          willPropagate = !1;
        }

        function requestPropagation() {
          if (willPropagate) {
            return;
          }
          willPropagate = !0;
          mw.requestIdleCallback(doPropagation, {
            timeout: 1
          });
        }

        function setAndPropagate(
            module, state) {
          registry[module].state = state;
          if (state === 'loaded' || state === 'ready' || state === 'error' || state === 'missing') {
            if (state === 'ready') {
              mw.loader.store.add(module);
            }
            else if (state === 'error' || state === 'missing') {
              errorModules.push(module);
            }
            requestPropagation();
          }
        }

        function sortDependencies(module, resolved, unresolved) {
          var i, skip, deps;
          if (!(module in registry)) {
            throw new Error('Unknown module: ' + module);
          }
          if (typeof registry[module].skip === 'string') {
            skip = (new Function(registry[module].skip)());
            registry[module].skip = !!skip;
            if (skip) {
              registry[module].dependencies = [];
              setAndPropagate(module, 'ready');
              return;
            }
          }
          if (!unresolved) {
            unresolved = new StringSet();
          }
          deps = registry[module].dependencies;
          unresolved.add(module);
          for (i = 0; i < deps.length; i++) {
            if (resolved.indexOf(deps[i]) === -1) {
              if (unresolved.has(deps[i])) {
                throw new Error('Circular reference detected: ' + module + ' -> ' + deps[i]);
              }
              sortDependencies(deps[i], resolved, unresolved);
            }
          }
          resolved.push(module);
        }

        function resolve(modules) {
          var resolved = baseModules.slice(),
              i = 0;
          for (; i < modules.length; i++) {
            sortDependencies(modules[i], resolved);
          }
          return resolved;
        }

        function resolveStubbornly(modules) {
          var saved, resolved = baseModules.slice(),
              i = 0;
          for (; i < modules.length; i++) {
            saved = resolved.slice();
            try {
              sortDependencies(modules[i], resolved);
            }
            catch (err) {
              resolved = saved;
              mw.log.warn('Skipped unresolvable module ' + modules[i]);
              if (modules[i] in registry) {
                mw.trackError('resourceloader.exception', {
                  exception: err,
                  source: 'resolve'
                });
              }
            }
          }
          return resolved;
        }

        function resolveRelativePath(relativePath, basePath) {
          var prefixes, prefix, baseDirParts, relParts = relativePath.match(/^((?:\.\.?\/)+)(.*)$/);
          if (!relParts) {
            return null;
          }
          baseDirParts = basePath.split('/');
          baseDirParts.pop();
          prefixes = relParts[1].split('/');
          prefixes.pop();
          while ((prefix = prefixes.pop()) !== undefined) {
            if (prefix === '..') {
              baseDirParts.pop();
            }
          }
          return (baseDirParts.length ? baseDirParts.join('/') + '/' : '') + relParts[2];
        }

        function makeRequireFunction(moduleObj, basePath) {
          return function require(moduleName) {
            var fileName, fileContent, result,
                moduleParam, scriptFiles = moduleObj.script.files;
            fileName = resolveRelativePath(moduleName, basePath);
            if (fileName === null) {
              return mw.loader.require(moduleName);
            }
            if (!hasOwn.call(scriptFiles, fileName)) {
              throw new Error('Cannot require undefined file ' + fileName);
            }
            if (hasOwn.call(moduleObj.packageExports, fileName)) {
              return moduleObj.packageExports[fileName];
            }
            fileContent = scriptFiles[fileName];
            if (typeof fileContent === 'function') {
              moduleParam = {
                exports: {}
              };
              fileContent(makeRequireFunction(moduleObj, fileName), moduleParam);
              result = moduleParam.exports;
            }
            else {
              result = fileContent;
            }
            moduleObj.packageExports[fileName] = result;
            return result;
          };
        }

        function addScript(src, callback) {
          var script = document.createElement('script');
          script.src = src;
          script.onload = script.onerror = function () {
            if (script.parentNode) {
              script.parentNode.removeChild(script);
            }
            if (callback) {
              callback();
              callback = null;
            }
          };
          document.head.appendChild(script);
        }

        function queueModuleScript(src, moduleName, callback) {
          pendingRequests.push(function () {
            if (moduleName !== 'jquery') {
              window.require = mw.loader.require;
              window.module = registry[moduleName].module;
            }
            addScript(src, function () {
              delete window.module;
              callback();
              if (pendingRequests[0]) {
                pendingRequests.shift()();
              }
              else {
                handlingPendingRequests = !1;
              }
            });
          });
          if (!handlingPendingRequests && pendingRequests[0]) {
            handlingPendingRequests = !0;
            pendingRequests.shift()();
          }
        }

        function addLink(url, media, nextNode) {
          var el = document.createElement('link');
          el.rel = 'stylesheet';
          if (media) {
            el.media = media;
          }
          el.href = url;
          if (nextNode && nextNode.parentNode) {
            nextNode.parentNode.insertBefore(el, nextNode);
          }
          else {
            document.head.appendChild(el);
          }
        }

        function domEval(code) {
          var script = document.createElement('script');
          if (mw.config.get('wgCSPNonce') !== false) {
            script.nonce = mw.config.get('wgCSPNonce');
          }
          script.text = code;
          document.head.appendChild(script);
          script.parentNode.removeChild(script);
        }

        function enqueue(dependencies, ready, error) {
          if (allReady(dependencies)) {
            if (ready !== undefined) {
              ready();
            }
            return;
          }
          if (anyFailed(dependencies)) {
            if (error !== undefined) {
              error(new Error(
                  'One or more dependencies failed to load'), dependencies);
            }
            return;
          }
          if (ready !== undefined || error !== undefined) {
            jobs.push({
              dependencies: dependencies.filter(function (module) {
                var state = registry[module].state;
                return state === 'registered' || state === 'loaded' || state === 'loading' || state === 'executing';
              }),
              ready: ready,
              error: error
            });
          }
          dependencies.forEach(function (module) {
            if (registry[module].state === 'registered' && queue.indexOf(module) === -1) {
              queue.push(module);
            }
          });
          mw.loader.work();
        }

        function execute(module) {
          var key, value, media, i, urls, cssHandle, siteDeps, siteDepErr, runScript, cssPending = 0;
          if (registry[module].state !== 'loaded') {
            throw new Error('Module in state "' + registry[module].state + '" may not execute: ' + module);
          }
          registry[module].state = 'executing';
          runScript = function () {
            var script, markModuleReady, nestedAddScript, mainScript;
            script = registry[module].script;
            markModuleReady = function () {
              setAndPropagate(module, 'ready');
            };
            nestedAddScript = function (arr, callback, i) {
              if (i >= arr.length) {
                callback();
                return;
              }
              queueModuleScript(arr[i], module, function () {
                nestedAddScript(arr, callback, i + 1);
              });
            };
            try {
              if (Array.isArray(script)) {
                nestedAddScript(script, markModuleReady, 0);
              }
              else if (typeof script === 'function' || (typeof script === 'object' && script !== null)) {
                if (typeof script === 'function') {
                  if (module === 'jquery') {
                    script();
                  }
                  else {
                    script(window.$, window.$, mw.loader.require, registry[module].module);
                  }
                }
                else {
                  mainScript = script.files[script.main];
                  if (typeof mainScript !== 'function') {
                    throw new Error('Main file in module ' + module + ' must be a function');
                  }
                  mainScript(makeRequireFunction(registry[module], script.main), registry[module].module);
                }
                markModuleReady();
              }
              else if (typeof script === 'string') {
                domEval(script);
                markModuleReady();
              }
              else {
                markModuleReady();
              }
            }
            catch (e) {
              setAndPropagate(module, 'error');
              mw.trackError('resourceloader.exception', {
                exception: e,
                module: module,
                source: 'module-execute'
              });
            }
          };
          if (registry[module].messages) {
            mw.messages.set(registry[module].messages);
          }
          if (registry[module].templates) {
            mw.templates.set(module, registry[module].templates);
          }
          cssHandle = function () {
            cssPending++;
            return function () {
              var runScriptCopy;
              cssPending--;
              if (cssPending === 0) {
                runScriptCopy = runScript;
                runScript = undefined;
                runScriptCopy();
              }
            };
          };
          if (registry[module].style) {
            for (key in registry[module].style) {
              value = registry[module].style[key];
              media = undefined;
              if (key !== 'url' && key !== 'css') {
                if (typeof value === 'string') {
                  addEmbeddedCSS(value, cssHandle());
                }
                else {
                  media = key;
                  key = 'bc-url';
                }
              }
              if (Array.isArray(value)) {
                for (i = 0; i < value.length; i++) {
                  if (key === 'bc-url') {
                    addLink(value[i], media, marker);
                  }
                  else if (key === 'css') {
                    addEmbeddedCSS(value[i], cssHandle());
                  }
                }
              }
              else if (typeof value === 'object') {
                for (media in value) {
                  urls = value[media];
                  for (i = 0; i < urls.length; i++) {
                    addLink(urls[i], media, marker);
                  }
                }
              }
            }
          }
          if (module === 'user') {
            try {
              siteDeps = resolve(['site']);
            }
            catch (e) {
              siteDepErr = e;
              runScript();
            }
            if (siteDepErr === undefined) {
              enqueue(siteDeps, runScript, runScript);
            }
          }
          else if (cssPending === 0) {
            runScript();
          }
        }

        function sortQuery(o) {
          var key, sorted = {},
              a = [];
          for (key in o) {
            a.push(key);
          }
          a.sort();
          for (key = 0; key < a.length; key++) {
            sorted[a[key]] = o[a[key]];
          }
          return sorted;
        }

        function buildModulesString(moduleMap) {
          var p, prefix, str = [],
              list = [];

          function restore(suffix) {
            return p + suffix;
          }

          for (prefix in moduleMap) {
            p = prefix === '' ? '' : prefix + '.';
            str.push(p + moduleMap[prefix].join(','));
            list.push.apply(list, moduleMap[prefix].map(restore));
          }
          return {
            str: str.join('|'),
            list: list
          };
        }

        function resolveIndexedDependencies(modules) {
          var i, j, deps;

          function resolveIndex(dep) {
            return typeof dep === 'number' ? modules[dep][0] : dep;
          }

          for (i = 0; i < modules.length; i++) {
            deps = modules[i][2];
            if (deps) {
              for (j = 0; j < deps.length; j++) {
                deps[j] = resolveIndex(deps[j]);
              }
            }
          }
        }

        function makeQueryString(params) {
          return Object.keys(params).map(function (key) {
            return encodeURIComponent(key) + '=' + encodeURIComponent(params[key]);
          }).join('&');
        }

        function batchRequest(batch) {
          var reqBase, splits, b, bSource, bGroup, source, group, i, modules, sourceLoadScript, currReqBase,
              currReqBaseLength, moduleMap, currReqModules, l, lastDotIndex, prefix, suffix, bytesAdded;

          function doRequest() {
            var query = Object.create(
                currReqBase),
                packed = buildModulesString(moduleMap);
            query.modules = packed.str;
            query.version = getCombinedVersion(packed.list);
            query = sortQuery(query);
            addScript(sourceLoadScript + '?' + makeQueryString(query));
          }

          if (!batch.length) {
            return;
          }
          batch.sort();
          reqBase = {
            "lang": "fr",
            "skin": "timeless"
          };
          splits = Object.create(null);
          for (b = 0; b < batch.length; b++) {
            bSource = registry[batch[b]].source;
            bGroup = registry[batch[b]].group;
            if (!splits[bSource]) {
              splits[bSource] = Object.create(null);
            }
            if (!splits[bSource][bGroup]) {
              splits[bSource][bGroup] = [];
            }
            splits[bSource][bGroup].push(batch[b]);
          }
          for (source in splits) {
            sourceLoadScript = sources[source];
            for (group in splits[source]) {
              modules = splits[source][group];
              currReqBase = Object.create(reqBase);
              if (group === 0 && mw.config.get('wgUserName') !== null) {
                currReqBase.user = mw.config.get('wgUserName');
              }
              currReqBaseLength = makeQueryString(currReqBase).length + 23;
              l = currReqBaseLength;
              moduleMap = Object.create(null);
              currReqModules = [];
              for (i = 0; i < modules.length; i++) {
                lastDotIndex = modules[i].lastIndexOf('.');
                prefix = modules[i].substr(0, lastDotIndex);
                suffix = modules[i].slice(lastDotIndex + 1);
                bytesAdded = moduleMap[prefix] ? suffix.length + 3 : modules[i].length + 3;
                if (currReqModules.length && l + bytesAdded > mw.loader.maxQueryLength) {
                  doRequest();
                  l = currReqBaseLength;
                  moduleMap = Object.create(null);
                  currReqModules = [];
                  mw.track('resourceloader.splitRequest', {
                    maxQueryLength: mw.loader.maxQueryLength
                  });
                }
                if (!moduleMap[prefix]) {
                  moduleMap[prefix] = [];
                }
                l += bytesAdded;
                moduleMap[prefix].push(suffix);
                currReqModules.push(modules[i]);
              }
              if (currReqModules.length) {
                doRequest();
              }
            }
          }
        }

        function asyncEval(implementations, cb) {
          if (!implementations.length) {
            return;
          }
          mw.requestIdleCallback(function () {
            try {
              domEval(implementations.join(';'));
            }
            catch (err) {
              cb(err);
            }
          });
        }

        function getModuleKey(module) {
          return module in registry ? (module + '@' + registry[module].version) : null;
        }

        function splitModuleKey(key) {
          var index = key.indexOf('@');
          if (index === -1) {
            return {
              name: key,
              version: ''
            };
          }
          return {
            name: key.slice(0, index),
            version: key.slice(index + 1)
          };
        }

        function registerOne(module,
                             version, dependencies, group, source, skip) {
          if (module in registry) {
            throw new Error('module already registered: ' + module);
          }
          registry[module] = {
            module: {
              exports: {}
            },
            packageExports: {},
            version: String(version || ''),
            dependencies: dependencies || [],
            group: typeof group === 'undefined' ? null : group,
            source: typeof source === 'string' ? source : 'local',
            state: 'registered',
            skip: typeof skip === 'string' ? skip : null
          };
        }

        return {
          moduleRegistry: registry,
          maxQueryLength: 5000,
          addStyleTag: newStyleTag,
          enqueue: enqueue,
          resolve: resolve,
          work: function () {
            var q, module, implementation, storedImplementations = [],
                storedNames = [],
                requestNames = [],
                batch = new StringSet();
            mw.loader.store.init();
            q = queue.length;
            while (q--) {
              module = queue[q];
              if (module in registry && registry[module].state === 'registered') {
                if (!batch.has(module)) {
                  registry[module].state = 'loading';
                  batch.add(module);
                  implementation = mw.loader.store.get(module);
                  if (implementation) {
                    storedImplementations.push(implementation);
                    storedNames.push(module);
                  }
                  else {
                    requestNames.push(module);
                  }
                }
              }
            }
            queue = [];
            asyncEval(
                storedImplementations,
                function (err) {
                  var failed;
                  mw.loader.store.stats.failed++;
                  mw.loader.store.clear();
                  mw.trackError('resourceloader.exception', {
                    exception: err,
                    source: 'store-eval'
                  });
                  failed = storedNames.filter(function (module) {
                    return registry[module].state === 'loading';
                  });
                  batchRequest(failed);
                });
            batchRequest(requestNames);
          },
          addSource: function (ids) {
            var id;
            for (id in ids) {
              if (id in sources) {
                throw new Error('source already registered: ' + id);
              }
              sources[id] = ids[id];
            }
          },
          register: function (modules) {
            var i;
            if (typeof modules === 'object') {
              resolveIndexedDependencies(modules);
              for (i = 0; i < modules.length; i++) {
                registerOne.apply(null, modules[i]);
              }
            }
            else {
              registerOne.apply(null, arguments);
            }
          },
          implement: function (module, script, style, messages, templates) {
            var split = splitModuleKey(module),
                name = split.name,
                version = split.version;
            if (!(name in registry)) {
              mw.loader.register(name);
            }
            if (registry[name].script !== undefined) {
              throw new Error('module already implemented: ' + name);
            }
            if (version) {
              registry[name].version = version;
            }
            registry[name].script = script || null;
            registry[name].style = style || null;
            registry[name].messages = messages || null;
            registry[name].templates = templates || null;
            if (registry[name].state !== 'error' && registry[name].state !== 'missing') {
              setAndPropagate(name, 'loaded');
            }
          },
          load: function (modules, type) {
            if (typeof modules === 'string' && /^(https?:)?\/?\//.test(modules)) {
              if (type === 'text/css') {
                addLink(modules);
              }
              else if (type === 'text/javascript' || type === undefined) {
                addScript(modules);
              }
              else {
                throw new Error('Invalid type ' + type);
              }
            }
            else {
              modules = typeof modules === 'string' ? [modules] : modules;
              enqueue(resolveStubbornly(modules), undefined, undefined);
            }
          },
          state: function (states) {
            var module, state;
            for (module in states) {
              state = states[module];
              if (!(module in registry)) {
                mw.loader.register(module);
              }
              setAndPropagate(module, state);
            }
          },
          getState: function (module) {
            return module in registry ? registry[module].state : null;
          },
          getModuleNames: function () {
            return Object.keys(registry);
          },
          require: function (moduleName) {
            var state = mw.loader.getState(moduleName);
            if (state !== 'ready') {
              throw new Error('Module "' + moduleName + '" is not loaded');
            }
            return registry[moduleName].module.exports;
          },
          store: {
            enabled: null,
            MODULE_SIZE_MAX: 1e5,
            items: {},
            queue: [],
            stats: {
              hits: 0,
              misses: 0,
              expired: 0,
              failed: 0
            },
            toJSON: function () {
              return {
                items: mw.loader.store.items,
                vary: mw.loader.store.vary,
                asOf: Math.ceil(Date.now() / 1e7)
              };
            },
            key: "MediaWikiModuleStore:frwiktionary",
            vary: "timeless:1-3:fr",
            init: function () {
              var raw, data;
              if (this.enabled !== null) {
                return;
              }
              if (!true || /Firefox/.test(navigator.userAgent)) {
                this.clear();
                this.enabled = !1;
                return;
              }
              try {
                raw = localStorage.getItem(this.key);
                this.enabled = !0;
                data = JSON.parse(raw);
                if (data && typeof data.items === 'object' && data.vary === this.vary && Date.now() < (data.asOf * 1e7) + 259e7) {
                  this.items = data.items;
                  return;
                }
              }
              catch (e) {
              }
              if (raw === undefined) {
                this.enabled = !1;
              }
            },
            get: function (module) {
              var key;
              if (this.enabled) {
                key = getModuleKey(module);
                if (key in this.items) {
                  this.stats.hits++;
                  return this.items[key];
                }
                this.stats.misses++;
              }
              return false;
            },
            add: function (module) {
              if (this.enabled) {
                this.queue.push(module);
                this.requestUpdate();
              }
            },
            set: function (module) {
              var key, args, src, encodedScript, descriptor = mw.loader.moduleRegistry[module];
              key = getModuleKey(module);
              if (key in this.items || !descriptor || descriptor.state !== 'ready' || !descriptor.version || descriptor.group === 1 || descriptor.group === 0 || [descriptor.script, descriptor.style, descriptor.messages, descriptor.templates].indexOf(undefined) !== -1) {
                return;
              }
              try {
                if (typeof descriptor.script === 'function') {
                  encodedScript = String(descriptor.script);
                }
                else if (typeof descriptor.script === 'object' && descriptor.script && !Array.isArray(descriptor.script)) {
                  encodedScript = '{' + 'main:' + JSON.stringify(descriptor.script.main) + ',' + 'files:{' + Object.keys(descriptor.script.files).map(function (key) {
                    var value = descriptor.script.files[key];
                    return JSON.stringify(key) + ':' + (typeof value === 'function' ? value : JSON.stringify(value));
                  }).join(',') + '}}';
                }
                else {
                  encodedScript = JSON.stringify(descriptor.script);
                }
                args = [JSON.stringify(key), encodedScript, JSON.stringify(descriptor.style), JSON.stringify(descriptor.messages), JSON.stringify(descriptor.templates)
                ];
              }
              catch (e) {
                mw.trackError('resourceloader.exception', {
                  exception: e,
                  source: 'store-localstorage-json'
                });
                return;
              }
              src = 'mw.loader.implement(' + args.join(',') + ');';
              if (src.length > this.MODULE_SIZE_MAX) {
                return;
              }
              this.items[key] = src;
            },
            prune: function () {
              var key, module;
              for (key in this.items) {
                module = key.slice(0, key.indexOf('@'));
                if (getModuleKey(module) !== key) {
                  this.stats.expired++;
                  delete this.items[key];
                }
                else if (this.items[key].length > this.MODULE_SIZE_MAX) {
                  delete this.items[key];
                }
              }
            },
            clear: function () {
              this.items = {};
              try {
                localStorage.removeItem(this.key);
              }
              catch (e) {
              }
            },
            requestUpdate: (function () {
              var hasPendingWrites = !1;

              function flushWrites() {
                var data, key;
                mw.loader.store.prune();
                while (mw.loader.store.queue.length) {
                  mw.loader.store.set(mw.loader.store.queue.shift());
                }
                key = mw.loader.store.key;
                try {
                  localStorage.removeItem(key);
                  data = JSON.stringify(mw.loader.store);
                  localStorage.setItem(key, data);
                }
                catch (e) {
                  mw.trackError('resourceloader.exception', {
                    exception: e,
                    source: 'store-localstorage-update'
                  });
                }
                hasPendingWrites = !1;
              }

              function onTimeout() {
                mw.requestIdleCallback(flushWrites);
              }

              return function () {
                if (!hasPendingWrites) {
                  hasPendingWrites = !0;
                  setTimeout(onTimeout, 2000);
                }
              };
            }())
          }
        };
      }())
    };
    window.mw = window.mediaWiki = mw;
  }());
  mw.requestIdleCallbackInternal = function (callback) {
    setTimeout(function () {
      var start = mw.now();
      callback({
        didTimeout: !1,
        timeRemaining: function () {
          return Math.max(0, 50 - (mw.now() - start));
        }
      });
    }, 1);
  };
  mw.requestIdleCallback = window.requestIdleCallback ? window.requestIdleCallback.bind(window) : mw.requestIdleCallbackInternal;
  (function () {
    var queue;
    mw.loader.addSource({
      "local": "/w/load.php",
      "metawiki": "//meta.wikimedia.org/w/load.php"
    });
    mw.loader.register([
      ["site", "zgyvc", [1]],
      ["site.styles", "1b2sp", [], 2],
      ["noscript", "r22l1", [], 3],
      ["filepage", "1yjvh"],
      ["user", "k1cuu", [], 0],
      ["user.styles", "8fimp", [], 0],
      ["user.defaults", "tlc5e"],
      ["user.options", "1hzgi", [6], 1],
      ["mediawiki.skinning.elements", "18v14"],
      ["mediawiki.skinning.content", "18v14"],
      ["mediawiki.skinning.interface", "12asu"],
      ["jquery.makeCollapsible.styles", "1aksq"],
      ["mediawiki.skinning.content.parsoid", "4t3vc"],
      ["mediawiki.skinning.content.externallinks", "fd9ti"],
      ["jquery", "yntai"],
      ["es6-promise", "1eg94", [], null, null, "return typeof Promise==='function'\u0026\u0026Promise.prototype.finally;"],
      ["mediawiki.base", "2v6em", [14]],
      ["jquery.chosen", "oqs2c"],
      ["jquery.client", "fwvev"],
      ["jquery.color", "dcjsx"],
      ["jquery.confirmable", "r7jxj", [111]],
      ["jquery.cookie", "13ckt"],
      ["jquery.form", "1wtf2"],
      ["jquery.fullscreen", "1xq4o"],
      ["jquery.highlightText", "1tsxs", [84]],
      ["jquery.hoverIntent", "1aklr"],
      ["jquery.i18n", "29w1w", [110]],
      ["jquery.lengthLimit", "1llrz", [67]],
      ["jquery.makeCollapsible", "1d1gt", [11]],
      ["jquery.mw-jump", "r425l"],
      ["jquery.spinner", "16kkr", [31]],
      ["jquery.spinner.styles", "o62ui"],
      ["jquery.jStorage", "1ccp7"],
      ["jquery.suggestions", "9e98z", [24]],
      ["jquery.tablesorter", "1bib8", [35, 112, 84]],
      ["jquery.tablesorter.styles", "ozpc4"],
      ["jquery.textSelection", "152er", [18]],
      [
        "jquery.throttle-debounce", "xl0tk"
      ],
      ["jquery.tipsy", "fsomm"],
      ["jquery.ui", "131e6"],
      ["moment", "16ves", [108, 84]],
      ["vue", "5urmd"],
      ["vuex", "c4upc", [15, 41]],
      ["mediawiki.template", "xae8l"],
      ["mediawiki.template.mustache", "nyt38", [43]],
      ["mediawiki.apipretty", "1cr6m"],
      ["mediawiki.api", "wbhlo", [72, 111]],
      ["mediawiki.content.json", "2o56x"],
      ["mediawiki.confirmCloseWindow", "16b49"],
      ["mediawiki.debug", "refdk", [200]],
      ["mediawiki.diff.styles", "1lsxd"],
      ["mediawiki.feedback", "jkfjy", [874, 208]],
      ["mediawiki.feedlink", "szobh"],
      ["mediawiki.filewarning", "1njr8", [200, 212]],
      ["mediawiki.ForeignApi", "191mv", [340]],
      ["mediawiki.ForeignApi.core", "sdvbu", [81, 46, 196]],
      ["mediawiki.helplink", "12yue"],
      ["mediawiki.hlist", "1egi4"],
      ["mediawiki.htmlform", "1fsyu", [27, 84]],
      ["mediawiki.htmlform.ooui", "j0ifc", [200]],
      ["mediawiki.htmlform.styles", "bkdt0"],
      ["mediawiki.htmlform.ooui.styles", "1f9kt"],
      ["mediawiki.icon", "j5ayk"],
      ["mediawiki.inspect", "f3swb", [67, 84]],
      ["mediawiki.notification", "9u87j", [84, 91]],
      [
        "mediawiki.notification.convertmessagebox", "3la3s", [64]
      ],
      ["mediawiki.notification.convertmessagebox.styles", "wj24b"],
      ["mediawiki.String", "15280"],
      ["mediawiki.pager.tablePager", "u9adc"],
      ["mediawiki.pulsatingdot", "tj1mg"],
      ["mediawiki.searchSuggest", "qavfw", [33, 46]],
      ["mediawiki.storage", "187em"],
      ["mediawiki.Title", "1trn1", [67, 84]],
      ["mediawiki.Upload", "f21ph", [46]],
      ["mediawiki.ForeignUpload", "u1osz", [54, 73]],
      ["mediawiki.ForeignStructuredUpload", "1e2u8", [74]],
      ["mediawiki.Upload.Dialog", "1rd88", [77]],
      ["mediawiki.Upload.BookletLayout", "1pqv7", [73, 82, 193, 40, 203, 208, 213, 214]],
      ["mediawiki.ForeignStructuredUpload.BookletLayout", "1fd1h", [75, 77, 115, 179, 173]],
      ["mediawiki.toc", "ckf9m", [88, 80]],
      ["mediawiki.toc.styles", "1e94g"],
      ["mediawiki.Uri", "sqmr8", [84]],
      ["mediawiki.user", "93pz6", [46, 88]],
      ["mediawiki.userSuggest", "18k7y", [33, 46]],
      ["mediawiki.util", "fil4j", [18]],
      ["mediawiki.viewport", "1vq57"],
      ["mediawiki.checkboxtoggle", "2yuhf"],
      ["mediawiki.checkboxtoggle.styles", "15kl9"],
      ["mediawiki.cookie", "33we7", [21]],
      ["mediawiki.experiments", "hufn5"],
      ["mediawiki.editfont.styles", "vdv4o"],
      ["mediawiki.visibleTimeout", "1trte"],
      ["mediawiki.action.delete", "p0q4m", [27, 200]],
      ["mediawiki.action.delete.file", "7jt29", [27, 200]],
      ["mediawiki.action.edit", "8n13s", [36, 95, 46, 90, 175]],
      ["mediawiki.action.edit.styles", "h0ulf"],
      ["mediawiki.action.edit.collapsibleFooter", "mu8ur", [28, 62, 71]],
      ["mediawiki.action.edit.preview", "12kh0", [30, 36, 50, 82, 200]],
      ["mediawiki.action.history", "vgbiv", [28]],
      ["mediawiki.action.history.styles", "1mrr9"],
      ["mediawiki.action.view.metadata", "wg72u", [107]],
      ["mediawiki.action.view.categoryPage.styles", "vu6r1"],
      ["mediawiki.action.view.postEdit", "aq7ek", [111, 64]],
      ["mediawiki.action.view.redirect", "q8iik", [18]],
      ["mediawiki.action.view.redirectPage", "1w50q"],
      ["mediawiki.action.edit.editWarning", "3rtnk", [36, 48, 111]],
      ["mediawiki.action.edit.watchlistExpiry", "8bngb", [200]],
      ["mediawiki.action.view.filepage", "1xmp4"],
      ["mediawiki.language", "1yioq", [109]],
      ["mediawiki.cldr", "erqtv", [110]],
      [
        "mediawiki.libs.pluralruleparser", "pvwvv"
      ],
      ["mediawiki.jqueryMsg", "1ch21", [108, 84, 7]],
      ["mediawiki.language.months", "1erd9", [108]],
      ["mediawiki.language.names", "1swib", [108]],
      ["mediawiki.language.specialCharacters", "nuqqt", [108]],
      ["mediawiki.libs.jpegmeta", "c4xwo"],
      ["mediawiki.page.gallery", "1lzpw", [37, 117]],
      ["mediawiki.page.gallery.styles", "jhck1"],
      ["mediawiki.page.gallery.slideshow", "13rvp", [46, 203, 222, 224]],
      ["mediawiki.page.ready", "cshts", [46]],
      ["mediawiki.page.startup", "cljv6"],
      ["mediawiki.page.watch.ajax", "1eb9d", [46]],
      ["mediawiki.page.image.pagination", "1hhs1", [30, 84]],
      ["mediawiki.rcfilters.filters.base.styles", "bth3k"],
      ["mediawiki.rcfilters.highlightCircles.seenunseen.styles", "16jii"],
      ["mediawiki.rcfilters.filters.dm", "1x21w", [81, 82, 196]],
      ["mediawiki.rcfilters.filters.ui", "16nbj", [28, 125, 170, 209, 216, 218, 219, 220, 222, 223]],
      ["mediawiki.interface.helpers.styles", "1xa94"],
      ["mediawiki.special", "pdnkj"],
      ["mediawiki.special.apisandbox", "rjy5z", [28, 170, 176, 199, 214, 219]],
      [
        "mediawiki.special.block", "1sg1p", [58, 173, 188, 180, 189, 186, 214, 216]
      ],
      ["mediawiki.misc-authed-ooui", "1dvz9", [59, 170, 175]],
      ["mediawiki.misc-authed-pref", "r18bc", [7]],
      ["mediawiki.misc-authed-curate", "1el0x", [20, 30, 46]],
      ["mediawiki.special.changeslist", "c83m6"],
      ["mediawiki.special.changeslist.enhanced", "19caq"],
      ["mediawiki.special.changeslist.legend", "1w3ma"],
      ["mediawiki.special.changeslist.legend.js", "ntrpi", [28, 88]],
      ["mediawiki.special.contributions", "wcllz", [28, 111, 173, 199]],
      ["mediawiki.special.edittags", "bg3e6", [17, 27]],
      ["mediawiki.special.import", "o75mv"],
      ["mediawiki.special.preferences.ooui", "1ys46", [48, 90, 65, 71, 180, 175]],
      ["mediawiki.special.preferences.styles.ooui", "1up4j"],
      ["mediawiki.special.recentchanges", "13ytr", [170]],
      ["mediawiki.special.revisionDelete", "1bzuu", [27]],
      ["mediawiki.special.search", "1cmha", [191]],
      ["mediawiki.special.search.commonsInterwikiWidget", "1ftcb", [81, 46]],
      ["mediawiki.special.search.interwikiwidget.styles", "1bmjh"],
      ["mediawiki.special.search.styles", "v73l4"],
      ["mediawiki.special.undelete", "19nu2", [170, 175]],
      ["mediawiki.special.unwatchedPages", "1wg7d", [46]],
      ["mediawiki.special.upload", "rmm5f", [30, 46, 48, 115, 128, 43]],
      ["mediawiki.special.userlogin.common.styles", "12rgj"],
      ["mediawiki.special.userlogin.login.styles", "lttkh"],
      ["mediawiki.special.createaccount", "10ksg", [46]],
      ["mediawiki.special.userlogin.signup.styles", "13aww"],
      ["mediawiki.special.userrights", "z5m70", [27, 65]],
      ["mediawiki.special.watchlist", "5myea", [46, 200, 219]],
      ["mediawiki.special.version", "1qu9b"],
      ["mediawiki.legacy.config", "1k3w5"],
      ["mediawiki.legacy.commonPrint", "1n3q6"],
      ["mediawiki.legacy.protect", "3jlou", [27]],
      ["mediawiki.legacy.shared", "ie2nk"],
      ["mediawiki.ui", "zu7ky"],
      ["mediawiki.ui.checkbox", "ekjft"],
      ["mediawiki.ui.radio", "thw7m"],
      ["mediawiki.ui.anchor", "1rlyw"],
      ["mediawiki.ui.button", "1dtxs"],
      ["mediawiki.ui.input", "flgrm"],
      ["mediawiki.ui.icon", "7pyxn"],
      ["mediawiki.widgets", "4iymh", [46, 171, 203, 213]],
      ["mediawiki.widgets.styles", "rqacs"],
      ["mediawiki.widgets.AbandonEditDialog", "j74go", [208]],
      ["mediawiki.widgets.DateInputWidget", "1p495", [174, 40, 203, 224]],
      ["mediawiki.widgets.DateInputWidget.styles", "2oyu8"],
      ["mediawiki.widgets.visibleLengthLimit", "1wyjs", [27, 200]],
      ["mediawiki.widgets.datetime", "1lmi0", [84, 200, 223, 224]],
      ["mediawiki.widgets.expiry", "19dtp", [176, 40, 203]],
      ["mediawiki.widgets.CheckMatrixWidget", "12na7", [200]],
      ["mediawiki.widgets.CategoryMultiselectWidget", "19ckj", [54, 203]],
      ["mediawiki.widgets.SelectWithInputWidget", "oe83m", [181, 203]],
      ["mediawiki.widgets.SelectWithInputWidget.styles", "1fufa"],
      ["mediawiki.widgets.SizeFilterWidget", "1rfut", [183, 203]],
      ["mediawiki.widgets.SizeFilterWidget.styles", "15b9u"],
      ["mediawiki.widgets.MediaSearch", "11eiu", [54, 203]],
      ["mediawiki.widgets.Table", "fhzym", [203]],
      ["mediawiki.widgets.UserInputWidget", "qnre9", [46, 203]],
      ["mediawiki.widgets.UsersMultiselectWidget", "1iec8", [46, 203]],
      ["mediawiki.widgets.NamespacesMultiselectWidget", "1nuht", [203]],
      ["mediawiki.widgets.TitlesMultiselectWidget", "2tq85", [170]],
      [
        "mediawiki.widgets.TagMultiselectWidget.styles", "1vzh9"
      ],
      ["mediawiki.widgets.SearchInputWidget", "1ri9j", [70, 170, 219]],
      ["mediawiki.widgets.SearchInputWidget.styles", "68its"],
      ["mediawiki.widgets.StashedFileWidget", "1hoew", [46, 200]],
      ["mediawiki.watchstar.widgets", "1ghpv", [199]],
      ["mediawiki.deflate", "gu4pi"],
      ["oojs", "1fhbo"],
      ["mediawiki.router", "1f8qs", [198]],
      ["oojs-router", "1xhla", [196]],
      ["oojs-ui", "yfxca", [206, 203, 208]],
      ["oojs-ui-core", "lgyln", [108, 196, 202, 201, 210]],
      ["oojs-ui-core.styles", "1xgjr"],
      ["oojs-ui-core.icons", "nlml2"],
      ["oojs-ui-widgets", "1dutn", [200, 205]],
      ["oojs-ui-widgets.styles", "1ldci"],
      ["oojs-ui-widgets.icons", "npai9"],
      ["oojs-ui-toolbars", "14793", [200, 207]],
      ["oojs-ui-toolbars.icons", "1p0pc"],
      ["oojs-ui-windows", "jguox", [200, 209]],
      ["oojs-ui-windows.icons", "1knyx"],
      ["oojs-ui.styles.indicators", "bgk8d"],
      ["oojs-ui.styles.icons-accessibility", "1nga8"],
      ["oojs-ui.styles.icons-alerts", "15987"],
      ["oojs-ui.styles.icons-content", "g5mcu"],
      ["oojs-ui.styles.icons-editing-advanced", "hnddm"],
      ["oojs-ui.styles.icons-editing-citation", "5cabn"],
      ["oojs-ui.styles.icons-editing-core", "hir4t"],
      ["oojs-ui.styles.icons-editing-list", "bsxoy"],
      ["oojs-ui.styles.icons-editing-styling", "u68hc"],
      ["oojs-ui.styles.icons-interactions", "ukbzy"],
      ["oojs-ui.styles.icons-layout", "1oqde"],
      ["oojs-ui.styles.icons-location", "r0vpl"],
      ["oojs-ui.styles.icons-media", "ycbz0"],
      ["oojs-ui.styles.icons-moderation", "1ldx9"],
      ["oojs-ui.styles.icons-movement", "bhqm2"],
      ["oojs-ui.styles.icons-user", "wib90"],
      ["oojs-ui.styles.icons-wikimedia", "eu1q7"],
      ["skins.vector.styles.legacy", "qots4"],
      ["skins.vector.styles", "re3f9"],
      ["skins.vector.icons", "d0v55"],
      ["skins.vector.styles.responsive", "1fx4s"],
      ["skins.vector.search", "yfxca", [41]],
      ["skins.vector.js", "fv4zc", [119]],
      ["skins.vector.legacy.js", "1jp0i", [119]],
      ["skins.monobook.styles", "1ykri"],
      ["skins.monobook.responsive", "1gwey"],
      ["skins.monobook.mobile", "1ax9y", [84]],
      ["skins.modern", "1ngr0"],
      ["skins.cologneblue", "c3te6"],
      ["skins.timeless", "xpmg3"],
      ["skins.timeless.js",
        "ktgsk"
      ],
      ["skins.timeless.mobile", "d5ocj"],
      ["ext.timeline.styles", "xg0ao"],
      ["ext.wikihiero", "1llrs"],
      ["ext.wikihiero.special", "1p77f", [243, 30, 200]],
      ["ext.wikihiero.visualEditor", "g1xea", [451]],
      ["ext.charinsert", "19mp5", [36]],
      ["ext.charinsert.styles", "1mhyc"],
      ["ext.cite.styles", "u9796"],
      ["ext.cite.style", "1r5f1"],
      ["ext.citeThisPage", "1ygkn"],
      ["ext.inputBox.styles", "1abiw"],
      ["ext.inputBox", "ae2hh", [37]],
      ["ext.pygments", "jz5u9"],
      ["ext.categoryTree", "7u57v", [46]],
      ["ext.categoryTree.styles", "1jrrm"],
      ["ext.spamBlacklist.visualEditor", "v2zpq"],
      ["mediawiki.api.titleblacklist", "wyv4b", [46]],
      ["ext.titleblacklist.visualEditor", "emzm0"],
      ["ext.quiz", "11ask"],
      ["ext.quiz.styles", "1jdmn"],
      ["mw.PopUpMediaTransform", "1k9md", [278, 72, 281, 262]],
      ["mw.PopUpMediaTransform.styles", "1ceg6"],
      ["mw.TMHGalleryHook.js", "1g8ta"],
      ["ext.tmh.embedPlayerIframe", "31nih", [297, 281]],
      ["mw.MediaWikiPlayerSupport", "isf2t", [296, 281]],
      ["mw.MediaWikiPlayer.loader", "1kyjg", [298, 313]],
      ["ext.tmh.video-js", "oycrt"],
      [
        "ext.tmh.videojs-ogvjs", "kgi48", [279, 267]
      ],
      ["ext.tmh.videojs-resolution-switcher", "1cf85", [267]],
      ["ext.tmh.mw-info-button", "1vsjj", [267, 72]],
      ["ext.tmh.player", "yzlxn", [278, 72]],
      ["ext.tmh.player.dialog", "1baso", [273, 275, 208]],
      ["ext.tmh.player.inline", "18prx", [270, 269]],
      ["ext.tmh.player.styles", "1sg7m"],
      ["ext.tmh.player.inline.styles", "zuann"],
      ["ext.tmh.thumbnail.styles", "2j0x5"],
      ["ext.tmh.transcodetable", "1s70s", [46, 199]],
      ["ext.tmh.OgvJsSupport", "5vtte"],
      ["ext.tmh.OgvJs", "10mqv", [278]],
      ["embedPlayerIframeStyle", "lkkli"],
      ["mw.MwEmbedSupport", "drvya", [282, 284, 294, 293, 285]],
      ["Spinner", "1913m", [84]],
      ["iScroll", "1tnmd"],
      ["jquery.loadingSpinner", "scnci"],
      ["mw.MwEmbedSupport.style", "1n6fe"],
      ["mediawiki.UtilitiesTime", "o55id"],
      ["mediawiki.client", "1ahv3"],
      ["mediawiki.absoluteUrl", "17zfv", [81]],
      ["mw.ajaxProxy", "ulh0j"],
      ["fullScreenApi", "4y6d4"],
      ["jquery.embedMenu", "123nf"],
      ["jquery.ui.touchPunch", "jqfnl", [39]],
      ["jquery.triggerQueueCallback", "dt3pe"],
      ["jquery.mwEmbedUtil", "16pz2"],
      [
        "jquery.debouncedresize", "rz9ui"
      ],
      ["mw.Api", "1ari9"],
      ["jquery.embedPlayer", "xxx6c"],
      ["mw.EmbedPlayer.loader", "1vehf", [297]],
      ["mw.MediaElement", "d4qk2", [278]],
      ["mw.MediaPlayer", "qwb7t"],
      ["mw.MediaPlayers", "1uolz", [300]],
      ["mw.MediaSource", "ubhxj", [281]],
      ["mw.EmbedTypes", "uzzuj", [81, 301]],
      ["mw.EmbedPlayer", "1ddt7", [290, 21, 295, 291, 25, 292, 286, 288, 287, 111, 307, 303, 299, 302]],
      ["mw.EmbedPlayerKplayer", "f4wup"],
      ["mw.EmbedPlayerGeneric", "rdm0a"],
      ["mw.EmbedPlayerNative", "1ic4s"],
      ["mw.EmbedPlayerVLCApp", "c3ijc", [81]],
      ["mw.EmbedPlayerIEWebMPrompt", "yt5k5"],
      ["mw.EmbedPlayerOgvJs", "j7uo6", [278, 30]],
      ["mw.EmbedPlayerImageOverlay", "tslgl"],
      ["mw.EmbedPlayerVlc", "1oc1c"],
      ["mw.TimedText.loader", "19pg5"],
      ["mw.TimedText", "11755", [113, 304, 315]],
      ["mw.TextSource", "3lvxc", [286, 289]],
      ["ext.urlShortener.special", "10k4r", [81, 59, 170, 199]],
      ["ext.urlShortener.toolbar", "mtx09", [46]],
      ["ext.securepoll.htmlform", "6qywv"],
      ["ext.securepoll", "yaakw"],
      ["ext.securepoll.special", "tfrzl"],
      ["ext.score.visualEditor", "1m0er", [322, 451]],
      ["ext.score.visualEditor.icons", "7hrzv"],
      ["ext.score.popup", "9c9o3", [46]],
      ["ext.score.errors", "1ag06"],
      ["ext.cirrus.serp", "12lbe", [81]],
      ["ext.cirrus.explore-similar", "1231u", [46, 44]],
      ["ext.nuke.confirm", "18lhc", [111]],
      ["ext.confirmEdit.editPreview.ipwhitelist.styles", "snao4"],
      ["ext.confirmEdit.visualEditor", "1o5d1", [846]],
      ["ext.confirmEdit.simpleCaptcha", "13yvy"],
      ["ext.confirmEdit.fancyCaptcha.styles", "1vin5"],
      ["ext.confirmEdit.fancyCaptcha", "1yib6", [46]],
      ["ext.confirmEdit.fancyCaptchaMobile", "1yib6", [509]],
      ["ext.centralauth", "qi1jg", [30, 84]],
      ["ext.centralauth.centralautologin", "16z1x", [111]],
      ["ext.centralauth.centralautologin.clearcookie", "1cv2l"],
      ["ext.centralauth.misc.styles", "ckz4t"],
      ["ext.centralauth.globaluserautocomplete", "i1ejb", [33, 46]],
      ["ext.centralauth.globalrenameuser", "1cnz7", [84]],
      ["ext.centralauth.ForeignApi", "1po5q", [55]],
      ["ext.widgets.GlobalUserInputWidget", "manwk", [46, 203]],
      ["ext.GlobalUserPage", "1jr7i"],
      ["ext.apifeatureusage", "1uio2"],
      ["ext.dismissableSiteNotice",
        "ylim6", [21, 84]
      ],
      ["ext.dismissableSiteNotice.styles", "1jwxr"],
      ["ext.centralNotice.startUp", "1dmh2", [348, 84]],
      ["ext.centralNotice.geoIP", "1q4sm", [21]],
      ["ext.centralNotice.choiceData", "125h5"],
      ["ext.centralNotice.display", "4cq0d", [347, 350, 649, 81, 71]],
      ["ext.centralNotice.kvStore", "1phlw"],
      ["ext.centralNotice.bannerHistoryLogger", "d1r9g", [349]],
      ["ext.centralNotice.impressionDiet", "i1yda", [349]],
      ["ext.centralNotice.largeBannerLimit", "14s7m", [349]],
      ["ext.centralNotice.legacySupport", "1u2eu", [349]],
      ["ext.centralNotice.bannerSequence", "12ugn", [349]],
      ["ext.centralNotice.freegeoipLookup", "v1vef", [347]],
      ["ext.centralNotice.bannerController", "yfxca", [347, 346]],
      ["ext.centralNotice.impressionEventsSampleRate", "1ig8o", [349]],
      ["ext.centralNotice.cspViolationAlert", "1jvwm"],
      ["ext.wikimediamessages.contactpage.affcomusergroup", "gj1hn"],
      ["mediawiki.special.block.feedback.request", "1eini"],
      ["ext.collection", "3xtlh", [364, 39, 108]],
      ["ext.collection.bookcreator.styles", "rv537"],
      ["ext.collection.bookcreator",
        "1crce", [363, 32]
      ],
      ["ext.collection.checkLoadFromLocalStorage", "gmc15", [362]],
      ["ext.collection.suggest", "16bak", [364]],
      ["ext.collection.offline", "m4ou0"],
      ["ext.collection.bookcreator.messageBox", "yfxca", [370, 369, 57]],
      ["ext.collection.bookcreator.messageBox.styles", "jo7wz"],
      ["ext.collection.bookcreator.messageBox.icons", "yijnl"],
      ["ext.ElectronPdfService.print.styles", "1868z"],
      ["ext.ElectronPdfService.special.styles", "1jjgx"],
      ["ext.ElectronPdfService.special.selectionImages", "uyjag"],
      ["ext.advancedSearch.initialstyles", "1dalr"],
      ["ext.advancedSearch.styles", "nkpv7"],
      ["ext.advancedSearch.searchtoken", "1v7b7", [], 1],
      ["ext.advancedSearch.elements", "rk2tv", [375, 81, 82, 203, 219, 220]],
      ["ext.advancedSearch.init", "1c7on", [377, 376]],
      ["ext.advancedSearch.SearchFieldUI", "ddgh2", [72, 203]],
      ["ext.abuseFilter", "1qpz7"],
      ["ext.abuseFilter.edit", "1rl1s", [30, 36, 46, 48, 203]],
      ["ext.abuseFilter.tools", "k7s70", [30, 46]],
      ["ext.abuseFilter.examine", "g9mbx", [30, 46]],
      ["ext.abuseFilter.ace", "1jikg", [628]],
      [
        "ext.abuseFilter.visualEditor", "1b19z"
      ],
      ["ext.wikiEditor", "2gg8d", [33, 36, 37, 39, 114, 82, 203, 213, 214, 215, 216, 217, 218, 222, 43], 4],
      ["ext.wikiEditor.styles", "ij13s", [], 4],
      ["ext.CodeMirror", "1snxi", [389, 36, 39, 82, 218]],
      ["ext.CodeMirror.data", "y2lc5"],
      ["ext.CodeMirror.lib", "1j2zw"],
      ["ext.CodeMirror.mode.mediawiki", "q1g67", [390]],
      ["ext.CodeMirror.lib.mode.css", "1h1a0", [390]],
      ["ext.CodeMirror.lib.mode.javascript", "uc431", [390]],
      ["ext.CodeMirror.lib.mode.xml", "1sqkp", [390]],
      ["ext.CodeMirror.lib.mode.htmlmixed", "guido", [392, 393, 394]],
      ["ext.CodeMirror.lib.mode.clike", "bm9wf", [390]],
      ["ext.CodeMirror.lib.mode.php", "238jg", [396, 395]],
      ["ext.CodeMirror.visualEditor.init", "14nnr"],
      ["ext.CodeMirror.visualEditor", "1xljn", [451]],
      ["ext.MassMessage.styles", "x1n8p"],
      ["ext.MassMessage.special.js", "qa56x", [27, 37, 39, 111]],
      ["ext.MassMessage.content.js", "1jnnc", [20, 39, 46]],
      ["ext.MassMessage.create", "f5yol", [39, 59, 111]],
      ["ext.MassMessage.edit", "1ekku", [175, 199]],
      ["ext.betaFeatures", "18v89", [18, 200]],
      [
        "ext.betaFeatures.styles", "h2xyt"
      ],
      ["mmv", "nf2hl", [19, 23, 37, 38, 81, 412]],
      ["mmv.ui.ondemandshareddependencies", "lc98k", [407, 199]],
      ["mmv.ui.download.pane", "1yk9g", [163, 170, 408]],
      ["mmv.ui.reuse.shareembed", "1ue74", [170, 408]],
      ["mmv.ui.tipsyDialog", "sesro", [407]],
      ["mmv.bootstrap", "1jshf", [167, 169, 414, 198]],
      ["mmv.bootstrap.autostart", "nvgyi", [412]],
      ["mmv.head", "1vvtn", [71, 82]],
      ["ext.linter.edit", "1ekuz", [36]],
      ["socket.io", "is39l"],
      ["dompurify", "1q6qs"],
      ["color-picker", "1qvmf"],
      ["unicodejs", "13wdo"],
      ["papaparse", "17t4y"],
      ["rangefix", "f32vh"],
      ["spark-md5", "11tzz"],
      ["ext.visualEditor.supportCheck", "13m8w", [], 5],
      ["ext.visualEditor.sanitize", "jrkg8", [417, 440], 5],
      ["ext.visualEditor.progressBarWidget", "qevve", [], 5],
      ["ext.visualEditor.tempWikitextEditorWidget", "1ess5", [90, 82], 5],
      ["ext.visualEditor.desktopArticleTarget.init", "ehpq1", [425, 423, 426, 437, 36, 81, 120, 71], 5],
      ["ext.visualEditor.desktopArticleTarget.noscript", "17h36"],
      ["ext.visualEditor.targetLoader", "mvzwb", [439, 437, 36, 81, 71, 82], 5],
      [
        "ext.visualEditor.desktopTarget", "erz1o", [], 5
      ],
      ["ext.visualEditor.desktopArticleTarget", "12q74", [443, 448, 430, 453], 5],
      ["ext.visualEditor.collabTarget", "1vlpn", [441, 447, 90, 170, 219, 220], 5],
      ["ext.visualEditor.collabTarget.desktop", "1j57r", [432, 448, 430, 453], 5],
      ["ext.visualEditor.collabTarget.init", "1isl9", [423, 170, 199], 5],
      ["ext.visualEditor.collabTarget.init.styles", "xc7ez"],
      ["ext.visualEditor.ve", "1scgz", [], 5],
      ["ext.visualEditor.track", "mi4nm", [436], 5],
      ["ext.visualEditor.core.utils", "9uq4f", [437, 199], 5],
      ["ext.visualEditor.core.utils.parsing", "1dfxr", [436], 5],
      ["ext.visualEditor.base", "1povc", [438, 439, 419], 5],
      ["ext.visualEditor.mediawiki", "1ga9a", [440, 429, 34, 679], 5],
      ["ext.visualEditor.mwsave", "113rd", [451, 27, 50, 219], 5],
      ["ext.visualEditor.articleTarget", "waudd", [452, 442, 172], 5],
      ["ext.visualEditor.data", "12kx7", [441]],
      ["ext.visualEditor.core", "gn4jc", [424, 423, 18, 420, 421, 422], 5],
      ["ext.visualEditor.commentAnnotation", "exw93", [445], 5],
      ["ext.visualEditor.rebase", "1i8m0", [418, 462, 446, 225, 416], 5],
      [
        "ext.visualEditor.core.desktop", "4hsf8", [445], 5
      ],
      ["ext.visualEditor.welcome", "3cozc", [199], 5],
      ["ext.visualEditor.switching", "1t8jc", [46, 199, 211, 214, 216], 5],
      ["ext.visualEditor.mwcore", "ugmv5", [463, 441, 450, 449, 127, 69, 12, 170], 5],
      ["ext.visualEditor.mwextensions", "yfxca", [444, 474, 467, 469, 454, 471, 456, 468, 457, 459], 5],
      ["ext.visualEditor.mwextensions.desktop", "yfxca", [452, 458, 78], 5],
      ["ext.visualEditor.mwformatting", "vi5g6", [451], 5],
      ["ext.visualEditor.mwimage.core", "101xf", [451], 5],
      ["ext.visualEditor.mwimage", "1gmqt", [455, 184, 40, 222, 226], 5],
      ["ext.visualEditor.mwlink", "3tde7", [451], 5],
      ["ext.visualEditor.mwmeta", "1xn3m", [457, 104], 5],
      ["ext.visualEditor.mwtransclusion", "1finx", [451, 186], 5],
      ["treeDiffer", "1g4bg"],
      ["diffMatchPatch", "kauq0"],
      ["ext.visualEditor.checkList", "10h4w", [445], 5],
      ["ext.visualEditor.diffing", "t2azj", [461, 445, 460], 5],
      ["ext.visualEditor.diffPage.init.styles", "1nm59"],
      ["ext.visualEditor.diffLoader", "te1ma", [429], 5],
      ["ext.visualEditor.diffPage.init", "sh0on", [465, 199, 211, 214], 5],
      [
        "ext.visualEditor.language", "zjzkl", [445, 679, 113], 5
      ],
      ["ext.visualEditor.mwlanguage", "5cf1m", [445], 5],
      ["ext.visualEditor.mwalienextension", "1ehhv", [451], 5],
      ["ext.visualEditor.mwwikitext", "5y8dw", [457, 90], 5],
      ["ext.visualEditor.mwgallery", "170u2", [451, 117, 184, 222], 5],
      ["ext.visualEditor.mwsignature", "1b83r", [459], 5],
      ["ext.visualEditor.experimental", "yfxca", [], 5],
      ["ext.visualEditor.icons", "yfxca", [475, 476, 212, 213, 214, 216, 217, 218, 219, 220, 223, 224, 225, 210], 5],
      ["ext.visualEditor.moduleIcons", "1dpzn"],
      ["ext.visualEditor.moduleIndicators", "1er04"],
      ["ext.citoid.visualEditor", "ty8mu", [787, 478]],
      ["ext.citoid.visualEditor.data", "zugge", [441]],
      ["ext.citoid.wikibase.init", "sypgy"],
      ["ext.citoid.wikibase", "fcmmc", [479, 39, 199]],
      ["ext.templateData", "1aivz"],
      ["ext.templateDataGenerator.editPage", "1alkm"],
      ["ext.templateDataGenerator.data", "ivp64", [196]],
      ["ext.templateDataGenerator.editTemplatePage", "f24ex", [481, 485, 483, 36, 679, 46, 203, 208, 219, 220]],
      ["ext.templateData.images", "k0y98"],
      ["ext.TemplateWizard",
        "17ova", [36, 170, 173, 186, 206, 208, 219]
      ],
      ["mediawiki.libs.guiders", "1wkvo"],
      ["ext.guidedTour.styles", "776h7", [487, 167]],
      ["ext.guidedTour.lib.internal", "1f1ga", [84]],
      ["ext.guidedTour.lib", "1oggz", [649, 489, 488]],
      ["ext.guidedTour.launcher", "k3952"],
      ["ext.guidedTour", "5neux", [490]],
      ["ext.guidedTour.tour.firstedit", "xek7p", [492]],
      ["ext.guidedTour.tour.test", "1igl7", [492]],
      ["ext.guidedTour.tour.onshow", "mxo6r", [492]],
      ["ext.guidedTour.tour.uprightdownleft", "1ity1", [492]],
      ["mobile.app", "e6qg3"],
      ["mobile.app.parsoid", "14q2a"],
      ["mobile.pagelist.styles", "1sz25"],
      ["mobile.pagesummary.styles", "1x5lq"],
      ["mobile.messageBox.styles", "9yeu5"],
      ["mobile.placeholder.images", "5cnzn"],
      ["mobile.userpage.styles", "13ooh"],
      ["mobile.startup.images", "1iopy"],
      ["mobile.init.styles", "68w1y"],
      ["mobile.init", "1xchx", [81, 509]],
      ["mobile.ooui.icons", "1k3c2"],
      ["mobile.user.icons", "1e61g"],
      ["mobile.startup", "7v5j3", [37, 121, 197, 71, 44, 167, 169, 82, 85, 501, 507, 499, 500, 502, 504]],
      ["mobile.editor.overlay", "5vaau", [48, 90, 64, 168, 172, 511,
        509, 508, 199, 216
      ]],
      ["mobile.editor.images", "1dpev"],
      ["mobile.talk.overlays", "1d5ai", [166, 510]],
      ["mobile.mediaViewer", "tgnsz", [509]],
      ["mobile.categories.overlays", "1xu5x", [510, 219]],
      ["mobile.languages.structured", "8jkp8", [509]],
      ["mobile.special.mobileoptions.styles", "51ao8"],
      ["mobile.special.mobileoptions.scripts", "np8t7", [509]],
      ["mobile.special.nearby.styles", "gk1d9"],
      ["mobile.special.userlogin.scripts", "131g5"],
      ["mobile.special.nearby.scripts", "r4ugr", [81, 518, 509]],
      ["mobile.special.mobilediff.images", "vxo8e"],
      ["skins.minerva.base.styles", "26kxb"],
      ["skins.minerva.content.styles", "ukkk7"],
      ["skins.minerva.content.styles.images", "pjmz7"],
      ["skins.minerva.icons.loggedin", "134jv"],
      ["skins.minerva.amc.styles", "1tmdg"],
      ["skins.minerva.overflow.icons", "wx6y7"],
      ["skins.minerva.icons.wikimedia", "1yjg3"],
      ["skins.minerva.icons.images.scripts", "yfxca", [530, 532, 533, 531]],
      ["skins.minerva.icons.images.scripts.misc", "qcej9"],
      ["skins.minerva.icons.page.issues.uncolored", "1ef8q"],
      [
        "skins.minerva.icons.page.issues.default.color", "osto0"
      ],
      ["skins.minerva.icons.page.issues.medium.color", "1x64d"],
      ["skins.minerva.mainPage.styles", "yiww6"],
      ["skins.minerva.userpage.styles", "1c1lg"],
      ["skins.minerva.talk.styles", "1e3g4"],
      ["skins.minerva.personalMenu.icons", "1bryb"],
      ["skins.minerva.mainMenu.advanced.icons", "16c44"],
      ["skins.minerva.mainMenu.icons", "uwdwc"],
      ["skins.minerva.mainMenu.styles", "p3py8"],
      ["skins.minerva.loggedin.styles", "14dd9"],
      ["skins.minerva.scripts", "llebw", [81, 89, 166, 509, 529, 539, 540]],
      ["skins.minerva.options", "1pw3i", [542]],
      ["ext.math.styles", "19kfl"],
      ["ext.math.scripts", "10354"],
      ["ext.math.wikibase.scripts", "1f29v", ["jquery.wikibase.entityselector"]],
      ["ext.math.visualEditor", "f3gfw", [544, 451]],
      ["ext.math.visualEditor.mathSymbolsData", "ck829", [547]],
      ["ext.math.visualEditor.mathSymbols", "1a66r", [548]],
      ["ext.math.visualEditor.chemSymbolsData", "ar9ku", [547]],
      ["ext.math.visualEditor.chemSymbols", "1rg9e", [550]],
      ["ext.babel", "1ordw"],
      ["ext.translate", "oi41z"],
      [
        "ext.translate.base", "pefzf", [46]
      ],
      ["ext.translate.dropdownmenu", "1metw"],
      ["ext.translate.specialpages.styles", "hqlwd"],
      ["ext.translate.loader", "dlda7"],
      ["ext.translate.messagetable", "17aaw", [554, 557, 562, 580, 37, 81]],
      ["ext.translate.pagetranslation.uls", "wbuxy", [669]],
      ["ext.translate.edit.documentation", "fgoly", [203, 208]],
      ["ext.translate.edit.documentation.styles", "1j16o"],
      ["ext.translate.parsers", "1kz7m", [84]],
      ["ext.translate.quickedit", "3066r"],
      ["ext.translate.selecttoinput", "emeil"],
      ["ext.translate.special.languagestats", "1dsgp", [34]],
      ["ext.translate.messagerenamedialog", "eqskr", [203, 208]],
      ["ext.translate.special.managetranslatorsandbox.styles", "1o2kq"],
      ["ext.translate.special.pagemigration", "15ps7", [46, 163, 167]],
      ["ext.translate.special.pagepreparation", "1rhe4", [46, 50, 163]],
      ["ext.translate.special.searchtranslations", "18lzl", [858, 852, 669]],
      ["ext.translate.special.translate", "1x7xn", [858, 852, 558, 851, 679]],
      ["ext.translate.special.translate.styles", "qv8j6"],
      [
        "ext.translate.special.translationstash", "l0l07", [858, 558, 579, 669]
      ],
      ["ext.translate.special.translationstats", "cttsf", [176]],
      ["ext.translate.statsbar", "1c8dh"],
      ["ext.translate.statstable", "1em1a"],
      ["ext.translate.tabgroup", "9z0s2"],
      ["ext.translate.tag.languages", "143yx"],
      ["ext.translate.translationstashstorage", "1rsst", [46]],
      ["jquery.textchange", "19f6s"],
      ["ext.translationnotifications.notifytranslators", "5c1eo", ["ext.translate.multiselectautocomplete", 39, 81, 82]],
      ["ext.translationnotifications.translatorsignup", "zz76i"],
      ["ext.vipsscaler", "vxgzo", [584]],
      ["jquery.ucompare", "1fqic"],
      ["ext.interwiki.specialpage", "1orww"],
      ["ext.echo.logger", "12wz2", [82, 196]],
      ["ext.echo.ui.desktop", "16hjv", [593, 588]],
      ["ext.echo.ui", "1ysp8", [589, 586, 861, 203, 212, 213, 219, 223, 224, 225]],
      ["ext.echo.dm", "1839i", [592, 40]],
      ["ext.echo.api", "xc75x", [54]],
      ["ext.echo.mobile", "a64rs", [588, 197, 44]],
      ["ext.echo.init", "14arh", [590]],
      ["ext.echo.styles.badge", "1xg7e"],
      ["ext.echo.styles.notifications", "1hygg"],
      [
        "ext.echo.styles.alert", "1jdxe"
      ],
      ["ext.echo.special", "1gtpv", [597, 588]],
      ["ext.echo.styles.special", "tjyvs"],
      ["ext.thanks.images", "1d4z5"],
      ["ext.thanks", "1rf02", [46, 88]],
      ["ext.thanks.corethank", "1t4sq", [599, 20, 208]],
      ["ext.thanks.mobilediff", "11h2b", [598, 509]],
      ["ext.thanks.flowthank", "7ktyj", [599, 208]],
      ["ext.flow.contributions", "1geaq"],
      ["ext.flow.contributions.styles", "14ji4"],
      ["ext.flow.templating", "1vnmc", [610, 82, 40]],
      ["ext.flow.mediawiki.ui.form", "1rwla"],
      ["ext.flow.styles.base", "1m4el"],
      ["ext.flow.board.styles", "w371w"],
      ["ext.flow.board.topic.styles", "18c1m"],
      ["mediawiki.template.handlebars", "1pcgr", [43]],
      ["ext.flow.components", "1snux", [618, 605, 37, 81, 196]],
      ["ext.flow.dm", "6vb36", [46, 196]],
      ["ext.flow.ui", "yqai1", [612, 616, 423, 90, 71, 82, 199, 214, 217, 225]],
      ["ext.flow", "1fy0v", [611, 617, 613]],
      ["ext.flow.visualEditor", "wvqyi", [616, 448, 430, 453, 470]],
      ["ext.flow.visualEditor.icons", "1ptcu"],
      ["ext.flow.jquery.conditionalScroll", "5qekk"],
      ["ext.flow.jquery.findWithParent", "jy8n3"],
      [
        "ext.disambiguator.visualEditor", "17hma", [458]
      ],
      ["ext.discussionTools.init", "msyyl", [439, 72, 81, 71, 40, 208, 421]],
      ["ext.discussionTools.debug", "10pl6", [620]],
      ["ext.discussionTools.ReplyWidget", "1t8ed", [846, 620, 172, 203]],
      ["ext.discussionTools.ReplyWidgetPlain", "1swxh", [622, 90, 82]],
      ["ext.discussionTools.ReplyWidgetVisual", "dvuaf", [622, 448, 430, 453, 472, 470]],
      ["ext.codeEditor", "otfyp", [626], 4],
      ["jquery.codeEditor", "1lfk5", [628, 627, 386, 208], 4],
      ["ext.codeEditor.icons", "vmy1x"],
      ["ext.codeEditor.ace", "bijbm", [], 6],
      ["ext.codeEditor.ace.modes", "lrng8", [628], 6],
      ["ext.scribunto.errors", "x4vzy", [39]],
      ["ext.scribunto.logs", "1pp6c"],
      ["ext.scribunto.edit", "1l878", [30, 46]],
      ["ext.RevisionSlider.lazyCss", "2ft4x"],
      ["ext.RevisionSlider.lazyJs", "6o1zu", [637, 224]],
      ["ext.RevisionSlider.init", "qzfj9", [640, 637, 639, 223]],
      ["ext.RevisionSlider.noscript", "1jaz7"],
      ["ext.RevisionSlider.Settings", "1bkrs", [71, 82]],
      ["ext.RevisionSlider.Pointer", "nclwc"],
      ["ext.RevisionSlider.Slider", "1ntxe", [641, 638, 39, 81, 224]],
      [
        "ext.RevisionSlider.RevisionList", "1411m", [40, 199]
      ],
      ["ext.RevisionSlider.HelpDialog", "ywo3z", [642, 199, 219]],
      ["ext.RevisionSlider.dialogImages", "96yrb"],
      ["ext.TwoColConflict.SplitJs", "126ed", [646, 647]],
      ["ext.TwoColConflict.SplitCss", "1qwpr"],
      ["ext.TwoColConflict.Split.TourImages", "1qjor"],
      ["ext.TwoColConflict.Split.Tour", "1nagb", [645, 69, 71, 82, 199, 219]],
      ["ext.TwoColConflict.Util", "9felx"],
      ["ext.TwoColConflict.JSCheck", "srrl2"],
      ["ext.eventLogging", "m0ftr", [82]],
      ["ext.eventLogging.debug", "148e2"],
      ["ext.eventLogging.jsonSchema", "1d66w"],
      ["ext.eventLogging.jsonSchema.styles", "e68l7"],
      ["ext.wikimediaEvents", "14ocp", [649, 81, 89, 71]],
      ["ext.wikimediaEvents.loggedin", "1y9oh", [81, 82]],
      ["ext.wikimediaEvents.wikibase", "ne6nw"],
      ["ext.navigationTiming", "19mrt", [649]],
      ["ext.navigationTiming.rumSpeedIndex", "hbh0o"],
      ["ext.uls.common", "iv20t", [679, 71, 82]],
      ["ext.uls.compactlinks", "zwwc1", [663, 167]],
      ["ext.uls.displaysettings", "1r8qe", [668, 669, 674, 164]],
      ["ext.uls.geoclient", "vzi6q", [88]],
      ["ext.uls.i18n",
        "148k0", [26, 84]
      ],
      ["ext.uls.init", "yfxca", [658]],
      ["ext.uls.inputsettings", "ggfkf", [864, 668, 165]],
      ["ext.uls.interface", "f503o", [674]],
      ["ext.uls.interlanguage", "143ce"],
      ["ext.uls.languagenames", "mnf58"],
      ["ext.uls.languagesettings", "bp0yr", [670, 671, 680, 167]],
      ["ext.uls.mediawiki", "105u5", [658, 667, 670, 678]],
      ["ext.uls.messages", "1rdve", [662]],
      ["ext.uls.preferences", "17uue", [82]],
      ["ext.uls.preferencespage", "ej2j1"],
      ["ext.uls.pt", "1whcz"],
      ["ext.uls.webfonts", "tv6ho", [658, 671]],
      ["ext.uls.webfonts.fonts", "yfxca", [676, 681]],
      ["ext.uls.webfonts.repository", "1x1bi"],
      ["jquery.ime", "19u95"],
      ["jquery.uls", "ab3zu", [26, 679, 680]],
      ["jquery.uls.data", "108k7"],
      ["jquery.uls.grid", "1mcjl"],
      ["jquery.webfonts", "1tvcc"],
      ["rangy.core", "177e2"],
      ["wikibase.client.init", "gvp8v"],
      ["wikibase.client.miscStyles", "78ef6"],
      ["wikibase.client.linkitem.init", "1u1m5", [30]],
      ["jquery.wikibase.linkitem", "ve5sw", [30, 38, 39, 54, 779, 778, 873]],
      ["wikibase.client.action.edit.collapsibleFooter", "154an", [28, 62, 71]],
      ["ext.wikimediaBadges",
        "1xybo"
      ],
      ["ext.TemplateSandbox.top", "1y9qm"],
      ["ext.TemplateSandbox", "54oct", [689]],
      ["ext.jsonConfig", "18hzd"],
      ["ext.jsonConfig.edit", "1nswk", [36, 185, 208]],
      ["ext.graph.styles", "1jtrv"],
      ["ext.graph.data", "lnpu6"],
      ["ext.graph.loader", "htqnv", [46]],
      ["ext.graph.vega1", "1gmql", [694, 81]],
      ["ext.graph.vega2", "quuuh", [694, 81]],
      ["ext.graph.sandbox", "1ytw8", [625, 697, 48]],
      ["ext.graph.visualEditor", "2jzjj", [694, 455, 185]],
      ["ext.MWOAuth.styles", "fns5c"],
      ["ext.MWOAuth.AuthorizeDialog", "1bu4e", [39]],
      ["ext.oath.totp.showqrcode", "1cqri"],
      ["ext.oath.totp.showqrcode.styles", "12n03"],
      ["ext.webauthn.ui.base", "1vzft", [111, 199]],
      ["ext.webauthn.register", "10875", [704, 46]],
      ["ext.webauthn.login", "1rg00", [704]],
      ["ext.webauthn.manage", "1lwel", [704, 46]],
      ["ext.webauthn.disable", "rncc1", [704]],
      ["ext.checkUser", "1ei42", [84]],
      ["ext.checkUser.investigate.styles", "eh5sl"],
      ["ext.checkUser.investigate", "jfucb", [34, 81, 71, 170, 214, 216, 219, 223, 225]],
      ["ext.checkUser.investigateblock.styles", "u9a69"],
      [
        "ext.checkUser.investigateblock", "1citu", [203]
      ],
      ["ext.guidedTour.tour.checkuserinvestigateform", "13nr5", [492]],
      ["ext.guidedTour.tour.checkuserinvestigate", "se9ou", [711, 492]],
      ["ext.quicksurveys.lib", "mkvs9", [649, 81, 89, 71, 85, 203]],
      ["ext.quicksurveys.init", "1ggqp"],
      ["ext.kartographer", "xr7un"],
      ["ext.kartographer.style", "rqxhz"],
      ["ext.kartographer.site", "1jxyp"],
      ["mapbox", "q1nn6"],
      ["leaflet.draw", "1tsje", [721]],
      ["ext.kartographer.link", "w48bu", [725, 197]],
      ["ext.kartographer.box", "ri4f5", [726, 737, 720, 719, 729, 81, 46, 222]],
      ["ext.kartographer.linkbox", "19jya", [729]],
      ["ext.kartographer.data", "q093m"],
      ["ext.kartographer.dialog", "1uan4", [721, 197, 203, 208, 219]],
      ["ext.kartographer.dialog.sidebar", "1psy6", [71, 219, 224]],
      ["ext.kartographer.util", "2hxgp", [718]],
      ["ext.kartographer.frame", "zrgfa", [724, 197]],
      ["ext.kartographer.staticframe", "194dp", [725, 197, 222]],
      ["ext.kartographer.preview", "16bnc"],
      ["ext.kartographer.editing", "qvghu", [46]],
      ["ext.kartographer.editor", "yfxca", [724, 722]],
      [
        "ext.kartographer.visualEditor", "12f2w", [729, 451, 37, 221]
      ],
      ["ext.kartographer.lib.prunecluster", "7wzxn", [721]],
      ["ext.kartographer.lib.topojson", "d8h09", [721]],
      ["ext.kartographer.wv", "xam9v", [736, 216]],
      ["ext.kartographer.specialMap", "gqd57"],
      ["ext.pageviewinfo", "1kswj", [697, 199]],
      ["three.js", "1uoe7"],
      ["ext.3d", "mno9h", [30]],
      ["ext.3d.styles", "1rrwr"],
      ["mmv.3d", "1okh4", [742, 407, 741]],
      ["mmv.3d.head", "15r4k", [742, 200, 211, 213]],
      ["ext.3d.special.upload", "l1rr1", [747, 151]],
      ["ext.3d.special.upload.styles", "tsx5r"],
      ["ext.GlobalPreferences.global", "1sy4f", [170, 178, 187]],
      ["ext.GlobalPreferences.global-nojs", "1ivhq"],
      ["ext.GlobalPreferences.local", "3dqkc", [178]],
      ["ext.GlobalPreferences.local-nojs", "qbqct"],
      ["ext.growthExperiments.mobileMenu.icons", "1mj9g"],
      ["ext.growthExperiments.SuggestedEditSession", "6bboh", [81, 82, 196]],
      ["ext.growthExperiments.Homepage.ConfirmEmail", "q8rns"],
      ["ext.growthExperiments.Homepage.ConfirmEmail.styles", "1wpll"],
      ["ext.growthExperiments.Homepage.Discovery.styles", "11igo"],
      [
        "ext.growthExperiments.HelpPanel.icons", "nogdi"
      ],
      ["ext.growthExperiments.welcomeSurvey.styles", "15js0"],
      ["ext.growthExperiments.HelpPanelCta.styles", "1rnpg"],
      ["ext.growthExperiments.Homepage.Logger", "1gpjo", [82, 200]],
      ["ext.growthExperiments.Homepage.Logging", "1jv94", [760, 81]],
      ["ext.growthExperiments.Homepage.RecentQuestions", "nm5y3", [46]],
      ["ext.growthExperiments.Homepage.Impact", "kq218", [760, 208]],
      ["ext.growthExperiments.Homepage.Mentorship", "73a6y", [771, 197]],
      ["ext.growthExperiments.Homepage.Topics", "1j5xg", [203]],
      ["ext.growthExperiments.Homepage.SuggestedEdits", "laauy", [760, 765, 81, 69, 208, 222]],
      ["ext.growthExperiments.Homepage.StartEditing", "adnnq", [760, 765, 208]],
      ["ext.growthExperiments.Homepage.icons", "13h41"],
      ["ext.growthExperiments.Homepage.contribs.styles", "1910z"],
      ["ext.growthExperiments.welcomeSurveyLanguage", "1fkuh", [197, 203]],
      ["ext.growthExperiments.Help", "em4en", [768, 81, 71, 82, 203, 208, 212, 214, 215, 216, 219, 225]],
      ["ext.growthExperiments.HelpPanel", "1yg3z", [771, 757, 759, 753, 69, 224]],
      ["ext.growthExperiments.HelpPanel.init", "1imq0", [753]],
      ["ext.growthExperiments.PostEdit", "1kilh", [768, 753, 208, 222]],
      ["ext.growthExperiments.confirmEmail.createAccount.styles", "1oi6q"],
      ["ext.growthExperiments.Homepage.styles", "newa8"],
      ["ext.growthExperiments.confirmEmail.createAccount", "129ka"],
      ["mw.config.values.wbSiteDetails", "o1ev5"],
      ["mw.config.values.wbRepo", "18viq"],
      ["ext.centralauth.globalrenamequeue", "yda79"],
      ["ext.centralauth.globalrenamequeue.styles", "182ui"],
      ["skins.monobook.mobile.echohack", "12ty6", [84, 212]],
      ["skins.monobook.mobile.uls", "82ivn", [665]],
      ["ext.cite.ux-enhancements", "1qp3f", [649]],
      ["ext.cite.visualEditor.core", "iqray", [451]],
      ["ext.cite.visualEditor.data", "1fjf8", [441]],
      ["ext.cite.visualEditor", "mk7kj", [249, 248, 785, 786, 459, 212, 215, 219]],
      ["ext.geshi.visualEditor", "2d69j", [451]],
      ["ext.gadget.SommaireDeveloppable", "ihwyv", [], 2],
      ["ext.gadget.HiddenQuote", "5xz4g", [88], 2],
      ["ext.gadget.cacheBoites", "1xxut", [], 2],
      ["ext.gadget.FlecheHaut", "uu5ad", [], 2],
      [
        "ext.gadget.AncreTitres", "1oorv", [84], 2
      ],
      ["ext.gadget.X-SAMPA", "1tzdg", [], 2],
      ["ext.gadget.Navigation_popups", "1iu39", [], 2],
      ["ext.gadget.OngletPurge", "73rme", [46], 2],
      ["ext.gadget.FilterTranslations", "68wlk", [84], 2],
      ["ext.gadget.anagrimes", "1lkhn", [], 2],
      ["ext.gadget.ChercheDansSousCategories", "17md5", [84], 2],
      ["ext.gadget.Subpages", "jl9hf", [84], 2],
      ["ext.gadget.specialchars", "1dijt", [84], 2],
      ["ext.gadget.Formatage", "1dowz", [], 2],
      ["ext.gadget.clearer-edit-summary", "mru50", [], 2],
      ["ext.gadget.WikEd", "uqyx9", [], 2],
      ["ext.gadget.bkl-check", "1bi9f", [], 2],
      ["ext.gadget.OngletGoogle", "2xpci", [84], 2],
      ["ext.gadget.SousPages", "1966q", [84], 2],
      ["ext.gadget.HotCat", "1lyot", [], 2],
      ["ext.gadget.Accessibility", "1qt14", [], 2],
      ["ext.gadget.searchbox", "j61e5", [], 2],
      ["ext.gadget.Barre_de_luxe", "1w4k0", [826], 2],
      ["ext.gadget.ResumeDeluxe", "156do", [4], 2],
      ["ext.gadget.translation_editor", "1lznx", [64], 2],
      ["ext.gadget.CreerFlexionFr", "1rhzf", [84], 2],
      ["ext.gadget.CreerNouveauMot", "x1rwc", [], 2],
      [
        "ext.gadget.CreerNouveauMot-ancien", "yb1nm", [], 2
      ],
      ["ext.gadget.CreerTrad", "bn74h", [84], 2],
      ["ext.gadget.DeluxeHistory", "1umye", [4, 84], 2],
      ["ext.gadget.MasquageRevisionsMultiples", "qen0w", [], 2],
      ["ext.gadget.RevertDiff", "tve0b", [], 2],
      ["ext.gadget.Smart_patrol", "1htp5", [], 2],
      ["ext.gadget.Wiktionnaire", "9josq", [826], 2],
      ["ext.gadget.StyleWiktionnaire", "z783t", [], 2],
      ["ext.gadget.AncienStyleWiktionnaire", "14mo8", [], 2],
      ["ext.gadget.LiensAncresDansCategories", "1kjvn", [], 2],
      ["ext.gadget.mediawiki.toolbar", "1plxx", [], 2],
      ["ext.gadget.RenommageCategorie", "1dwhe", [], 2],
      ["ext.gadget.IntersectionCategorie", "148i5", [], 2],
      ["ext.gadget.TabbedLanguages2", "1anw1", [], 2],
      ["ext.gadget.TargetedTranslations", "192fi", [], 2],
      ["ext.gadget.Wiktoolbar", "ab2vl", [], 2],
      ["ext.gadget.Wiktoolbar-caracteres", "1wsxd", [], 2],
      ["ext.gadget.adddefinition", "a6iwb", [84], 2],
      ["ext.gadget.WiktSidebarTranslation", "doq0b", [], 2],
      ["ext.gadget.FastRevert", "1ae4n", [], 2],
      ["ext.gadget.interProjets", "iu7ij", [84, 21], 2],
      [
        "ext.gadget.HideCategories", "1d54t", [], 2
      ],
      ["ext.gadget.GoogleTrans", "1kcaa", [], 2],
      ["ext.gadget.doublewiki", "1mdet", [], 2],
      ["ext.gadget.LiveRC", "1q17z", [], 2],
      ["ext.gadget.CreerNouveauMot-dev", "1fd5m", [84], 2],
      ["ext.gadget.Barre_de_luxe-dev", "oke51", [826], 2],
      ["ext.gadget.specialchars-dev", "17u15", [84], 2],
      ["ext.gadget.AjouterCitation-dev", "j6ki6", [], 2],
      ["ext.gadget.externalsearch", "h2lgo", [], 2],
      ["ext.confirmEdit.CaptchaInputWidget", "1xrfp", [200]],
      ["ext.globalCssJs.user", "qvuzj", [], 0, "metawiki"],
      ["ext.globalCssJs.user.styles", "qvuzj", [], 0, "metawiki"],
      ["pdfhandler.messages", "1s3kj"],
      ["ext.guidedTour.tour.firsteditve", "16a94", [492]],
      ["ext.translate.recentgroups", "1eiup", [71]],
      ["ext.translate.groupselector", "h0duu", [554, 557, 575, 39]],
      ["ext.translate.special.aggregategroups", "dgcqs", [39, 46]],
      ["ext.translate.special.importtranslations", "weikr", [39]],
      ["ext.translate.special.managetranslatorsandbox", "1kply", [557, 579, 669, 39]],
      ["ext.translate.special.searchtranslations.operatorsuggest", "1of83", [39]],
      [
        "ext.translate.special.pagetranslation", "19bay", [81, 167, 170]
      ],
      ["ext.translate.editor", "ga9xz", [554, 555, 28, 36, 580, 81, 82]],
      ["ext.translate.special.managegroups", "i7fbt", [566]],
      ["ext.echo.emailicons", "18m6x"],
      ["ext.echo.secondaryicons", "hgjty"],
      ["ext.guidedTour.tour.flowOptIn", "1qdcq", [492]],
      ["ext.wikimediaEvents.visualEditor", "16fqb", [429]],
      ["ext.uls.ime", "1gy9u", [669, 671, 677]],
      ["ext.uls.setlang", "1j4w7", [81, 46, 167]],
      ["ext.guidedTour.tour.helppanel", "1jj6u", [492]],
      ["ext.guidedTour.tour.homepage_mentor", "1muit", [492]],
      ["ext.guidedTour.tour.homepage_welcome", "1hsjg", [492]],
      ["ext.guidedTour.tour.homepage_discovery", "i4fwp", [492]],
      ["ext.guidedTour.tour.RcFiltersIntro", "15ltp", [492]],
      ["ext.guidedTour.tour.WlFiltersIntro", "6h3qk", [492]],
      ["ext.guidedTour.tour.RcFiltersHighlight", "8l6d5", [492]],
      ["wikibase.Site", "9d40m", [669]],
      ["mediawiki.messagePoster", "1vt3v", [54]]
    ]);
    mw.config.set(window.RLCONF || {});
    mw.loader.state(window.RLSTATE || {});
    mw.loader.load(window.RLPAGEMODULES || []);
    queue = window.RLQ || [];
    RLQ = [];
    RLQ.push = function (fn) {
      if (typeof fn === 'function') {
        fn();
      }
      else {
        RLQ[RLQ.length] = fn;
      }
    };
    while (queue[0]) {
      RLQ.push(queue.shift());
    }
    NORLQ = {
      push: function () {
      }
    };
  }());
}
