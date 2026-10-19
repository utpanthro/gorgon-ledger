(() => {
  'use strict';

  const prefix = 'gorgon-';
  const endpoints = [`${location.origin}/api/save`];
  if (location.hostname === '127.0.0.1' && location.port === '4173') {
    endpoints.push('http://127.0.0.1:4175/api/save');
  }
  let endpoint = endpoints[0];
  const original = {
    setItem: Storage.prototype.setItem,
    removeItem: Storage.prototype.removeItem,
    clear: Storage.prototype.clear
  };
  let timer = 0;
  let saving = false;
  let dirty = false;

  const snapshot = () => {
    const data = {};
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (key?.startsWith(prefix)) data[key] = localStorage.getItem(key);
    }
    return data;
  };

  const parseValue = value => {
    try { return JSON.parse(value); } catch { return value; }
  };

  const mergeValue = (localValue, fileValue) => {
    if (fileValue === undefined) return localValue;
    if (localValue === undefined) return fileValue;
    const local = parseValue(localValue);
    const file = parseValue(fileValue);
    if (Array.isArray(local) && Array.isArray(file)) {
      return JSON.stringify([...new Set([...local, ...file])]);
    }
    if (local && file && typeof local === 'object' && typeof file === 'object') {
      return JSON.stringify({ ...local, ...file });
    }
    return fileValue;
  };

  const replaceBrowserCopy = data => {
    const currentKeys = [];
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (key?.startsWith(prefix)) currentKeys.push(key);
    }
    currentKeys.forEach(key => original.removeItem.call(localStorage, key));
    Object.entries(data).forEach(([key, value]) => original.setItem.call(localStorage, key, value));
  };

  const postSync = (data, target = endpoint) => {
    const request = new XMLHttpRequest();
    request.open('POST', target, false);
    request.setRequestHeader('Content-Type', 'text/plain;charset=UTF-8');
    request.send(JSON.stringify({ data }));
    return request.status >= 200 && request.status < 300;
  };

  const hydrate = () => {
    for (const target of endpoints) {
      try {
        const request = new XMLHttpRequest();
        request.open('GET', target, false);
        request.send();
        if (request.status < 200 || request.status >= 300) continue;
        endpoint = target;
        const response = JSON.parse(request.responseText);
        const local = snapshot();
        if (!response.exists) {
          if (Object.keys(local).length) postSync(local, target);
          return true;
        }
        const file = response.data || {};
        const merged = {};
        for (const key of new Set([...Object.keys(local), ...Object.keys(file)])) {
          merged[key] = mergeValue(local[key], file[key]);
        }
        replaceBrowserCopy(merged);
        if (JSON.stringify(merged) !== JSON.stringify(file)) postSync(merged, target);
        return true;
      } catch (error) {
        console.warn(`Local save endpoint unavailable: ${target}`, error);
      }
    }
    console.warn('File-backed saves are unavailable; using browser storage.');
    return false;
  };

  const flush = async () => {
    if (saving) { dirty = true; return; }
    saving = true;
    do {
      dirty = false;
      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
          body: JSON.stringify({ data: snapshot() }),
          cache: 'no-store'
        });
        if (!response.ok) throw new Error(`Save failed with status ${response.status}`);
      } catch (error) {
        console.warn('Could not write the local save file.', error);
      }
    } while (dirty);
    saving = false;
  };

  const schedule = () => {
    dirty = true;
    clearTimeout(timer);
    timer = window.setTimeout(flush, 120);
  };

  const fileStorageAvailable = hydrate();

  Storage.prototype.setItem = function(key, value) {
    original.setItem.call(this, key, value);
    if (this === localStorage && String(key).startsWith(prefix) && fileStorageAvailable) schedule();
  };
  Storage.prototype.removeItem = function(key) {
    original.removeItem.call(this, key);
    if (this === localStorage && String(key).startsWith(prefix) && fileStorageAvailable) schedule();
  };
  Storage.prototype.clear = function() {
    original.clear.call(this);
    if (this === localStorage && fileStorageAvailable) schedule();
  };

  window.addEventListener('pagehide', () => {
    if (fileStorageAvailable && dirty) {
      navigator.sendBeacon(endpoint, new Blob([JSON.stringify({ data: snapshot() })], { type: 'text/plain;charset=UTF-8' }));
    }
  });

  window.GorgonFileStorage = { available: fileStorageAvailable, flush };
})();
