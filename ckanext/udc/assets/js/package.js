this.ckan.module('package-form', function ($) {
  return {
    initialize: function () {
      this._lockForm();
      try {
        var configuredLangs = Array.isArray(window.udcLangs) ? window.udcLangs.slice() : [];
        this.langs = configuredLangs.length ? configuredLangs : ['en'];
        this.defaultLang = window.udcDefaultLang || this.langs[0] || 'en';
        if (this.langs.indexOf(this.defaultLang) === -1) this.langs.unshift(this.defaultLang);
        this.currentLang = window.udcCurrentLang || this.defaultLang;
        if (this.langs.indexOf(this.currentLang) === -1) this.langs.push(this.currentLang);
        this.currentLang = this.langs.indexOf(this.currentLang) !== -1 ? this.currentLang : this.defaultLang;
        this.pkgConfig = window.packageConfig || [];

        this._initTooltips();
        this._initLicenseDropdown();
        this._initNewLicenseForm();

        // Ensure core title/notes fields participate in multilingual helpers
        this._prepareCoreI18n('title', '#field-title');
        this._prepareCoreI18n('notes', '#field-notes');
        this._prepareCoreI18n('notes', '#field-description');
        this._prepareCoreI18n('tags', '#field-tags');

        // Multilingual: sync hidden JSON for custom text fields
        this._initI18nHiddenGroups();

        // Language toggles (per-field + per-level)
        this._initLangToggles();

        // Multiple select widgets (labels localized where needed)
        this._initMultipleSelects();

        // Progress bars (existing logic)
        this._initProgressTracking();

        // Version relationship fields (single + multiple)
        this._initVersionDataset();
        this._initDatasetVersions();

        // Default all levels to configured default language on load
        var self = this;
        (this.pkgConfig || []).forEach(function (_level, i) {
          self._applyLangToLevel(i, self.currentLang);
        });
        this._applyLangToField('title', this.currentLang);
        this._applyLangToField('notes', this.currentLang);
        this._applyLangToField('tags', this.currentLang);
      } finally {
        this._unlockForm();
      }
    },

    // ===== UI basics =====
    _initTooltips: function () {
      var list = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
      list.map(function (el) { return new bootstrap.Tooltip(el); });
    },

    _initLicenseDropdown: function () {
      var licenses = window.packageLicenses || [];
      var options = licenses.map(function (l) {
        return {
          label: '<div>' + l[1] +
                 (l[2] ? '<a class="ms-1" style="font-size:12px;vertical-align:text-bottom;" href="' + l[2] + '" target="_blank"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>' : '') +
                 '</div>',
          value: l[0]
        };
      });
      var ele = document.querySelector('#field-license_id');
      if (!ele) return;
      var selectedValue = ele.getAttribute('value') || '';
      VirtualSelect.init({
        ele: '#field-license_id',
        search: true, multiple: false, maxWidth: '100%',
        placeholder: this._('Please select the license'),
        options: options, selectedValue: selectedValue,
        hasOptionDescription: false, optionsCount: 6, optionHeight: '40px'
      });
    },

    _initNewLicenseForm: function () {
      var btn = document.querySelector('#add-license-popover-btn');
      var box = document.querySelector('.add-license-container');
      if (btn && box) btn.addEventListener('click', function () {
        box.classList.toggle('visible'); box.classList.toggle('hidden');
      });

      var form = document.getElementById('create-license-form');
      if (!form) return;
      form.onsubmit = async function (e) {
        e.preventDefault();
        var api = document.getElementById('license-create-api').value;
        var fd = new FormData(form);
        var resp = await fetch(api, { method: 'POST', body: fd });

        var errBox = document.getElementById('new-license-error');
        var okBox = document.getElementById('new-license-success');

        if (resp.status >= 400) {
          var err = {}; try { err = await resp.json(); } catch(_e){}
          if (err && err.error && err.error.message) {
            errBox.innerHTML = '<i class="fa-solid fa-circle-exclamation" style="padding-right:5px"></i><span>' + err.error.message + '</span>';
            errBox.classList.remove('d-none'); okBox.classList.add('d-none');
          }
        } else {
          var vs = document.querySelector('#field-license_id');
          if (vs && vs.addOption) { vs.addOption({ value: fd.get('id'), label: fd.get('title') }); vs.setValue(fd.get('id')); }
          errBox.innerHTML = ''; errBox.classList.add('d-none'); okBox.classList.remove('d-none');
        }
      };
    },

  // ===== Prepare core translated fields (title/notes/tags) =====
    _prepareCoreI18n: function (groupName, selector) {
      var input = document.querySelector(selector);
      if (!input) return;
      input.classList.add('udc-i18n-input');
      input.setAttribute('data-lang', this.defaultLang);
      input.setAttribute('data-i18n-for', groupName);
    },

    // ===== I18N hidden JSON for custom TEXT fields =====
    _initI18nHiddenGroups: function () {
      var self = this;
      var hiddens = document.querySelectorAll('[data-i18n-hidden]');
      hiddens.forEach(function (hid) {
        var name = hid.getAttribute('data-i18n-hidden');
        var format = hid.getAttribute('data-i18n-format') || 'string';
        var inputs = document.querySelectorAll('.udc-i18n-input[data-i18n-for="' + name + '"]');

        // prefill from hidden
        try {
          if (hid.value) {
            var obj = JSON.parse(hid.value);
            inputs.forEach(function (inp) {
              var L = inp.getAttribute('data-lang');
              if (!obj) return;
              var stored = obj[L];
              if (format === 'list' && Array.isArray(stored)) {
                inp.value = stored.join(', ');
              } else if (typeof stored === 'string') {
                inp.value = stored;
              } else if (stored != null) {
                inp.value = String(stored);
              }
            });
            if (name === 'tags') self._syncTagString(obj);
          }
        } catch(_e){}

        var update = function () {
          var collected = self._collectI18nValues(name, format);
          hid.value = collected.json;
          if (name === 'tags') self._syncTagString(collected.parsed);
        };
        inputs.forEach(function (inp) {
          inp.addEventListener('input', update);
          inp.addEventListener('change', update);
        });
        update();
      });
    },

    _collectI18nValues: function (name, format) {
      var out = {};
      var inputs = document.querySelectorAll('.udc-i18n-input[data-i18n-for="' + name + '"]');
      inputs.forEach(function (inp) {
        var L = inp.getAttribute('data-lang');
        if (!L) return;
        var raw = inp.value;
        if (typeof raw !== 'string') raw = '';
        raw = raw.trim();
        if (!raw) return;
        if (format === 'list') {
          var parts = raw.split(/[\n,]+/).map(function (piece) {
            return piece.trim();
          }).filter(function (piece) { return piece.length > 0; });
          if (parts.length) out[L] = parts;
        } else {
          out[L] = raw;
        }
      });
      return {
        parsed: out,
        json: Object.keys(out).length ? JSON.stringify(out) : ''
      };
    },

    _syncTagString: function (parsed) {
      var input = document.querySelector('#field-tags');
      if (!input) return;
      var val = parsed ? parsed[this.defaultLang] : null;
      var arr;
      if (Array.isArray(val)) {
        arr = val.slice();
      } else if (typeof val === 'string' && val.trim()) {
        arr = val.split(/[\n,]+/).map(function (piece) { return piece.trim(); }).filter(function (piece) { return piece.length > 0; });
      } else {
        arr = [];
      }
      input.value = arr.join(', ');
    },

    _lockForm: function () {
      this._loadingOverlay = document.getElementById('udc-form-loading-overlay');
      if (this._loadingOverlay) {
        this._loadingOverlay.classList.remove('d-none');
        this._loadingOverlay.removeAttribute('aria-hidden');
      }
      document.querySelectorAll('[data-udc-disable-on-load]').forEach(function (el) {
        el.dataset.udcLocked = 'true';
        if (el.tagName === 'BUTTON' || el.tagName === 'INPUT') {
          el.setAttribute('disabled', 'disabled');
        } else {
          if (!el.dataset.udcOriginalTabindex) {
            el.dataset.udcOriginalTabindex = el.hasAttribute('tabindex') ? el.getAttribute('tabindex') : '__none__';
          }
          if (!el.dataset.udcOriginalAriaDisabled) {
            el.dataset.udcOriginalAriaDisabled = el.hasAttribute('aria-disabled') ? el.getAttribute('aria-disabled') : '__none__';
          }
          el.classList.add('disabled');
          el.setAttribute('aria-disabled', 'true');
          el.setAttribute('tabindex', '-1');
        }
      });
    },

    // ===== Version relationship helpers =====
    _parseJsonSafe: function (value, fallback) {
      if (fallback === undefined) fallback = null;
      if (value == null || value === '') return fallback;
      if (typeof value === 'object') return value;
      try {
        return JSON.parse(String(value));
      } catch (e) {
        return fallback;
      }
    },

    _stringifyOrEmpty: function (obj) {
      if (!obj || (typeof obj === 'object' && Object.keys(obj).length === 0)) return '';
      try { return JSON.stringify(obj); } catch (e) { return ''; }
    },

    _isCudcCatalogueUrl: function (url) {
      if (!url || typeof url !== 'string') return false;
      return url.indexOf('/catalogue/') !== -1;
    },

    _updateVersionTitleDisabled: function (inputUrl, inputTitle) {
      if (!inputUrl || !inputTitle) return;
      var url = inputUrl.value || '';
      var isCudc = this._isCudcCatalogueUrl(url.trim());
      inputTitle.readOnly = !!isCudc;
      inputTitle.classList.toggle('disabled', !!isCudc);
    },

    _versionMetaApiUrl: function () {
      // Simple convention: backend can expose this via config or window var later
      if (window.udcVersionMetaApi) return window.udcVersionMetaApi;
      return '/api/3/action/udc_version_meta';
    },

    _fetchVersionMeta: async function (url) {
      if (!url) return null;
      try {
        var resp = await fetch(this._versionMetaApiUrl(), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: url })
        });
        if (!resp.ok) return null;
        var data = await resp.json();
        if (data && data.success && data.result) {
          return data.result;
        }
      } catch (e) {
        // swallow; UI will simply not auto-fill
      }
      return null;
    },

    _initVersionDataset: function () {
      var wrapper = document.getElementById('version-dataset-wrapper');
      var hidden = document.getElementById('field-version_dataset');
      if (!wrapper || !hidden) return;
      var self = this;

      // Build structure: Row1 URL+button, Row2 Title, Row3 Description
      var row1 = document.createElement('div');
      row1.className = 'row g-2 align-items-end mb-1';
      row1.innerHTML = '' +
        '<div class="col-md-8 col-lg-7">' +
          '<div class="control-medium">' +
            '<label class="form-label small" for="field-version_dataset_url_dummy">' + self._('URL') + '</label>' +
            '<div class="controls">' +
              '<input id="field-version_dataset_url_dummy" type="text" name="version_dataset_url_dummy" class="form-control" data-version-field="url" />' +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div class="col-md-4 col-lg-5 d-flex align-items-end">' +
          '<button type="button" class="btn btn-outline-primary w-100" id="version-dataset-fetch" data-udc-disable-on-load>' + self._('Auto-fill') + '</button>' +
        '</div>';

      var row2 = document.createElement('div');
      row2.className = 'row g-2 mb-2';
      row2.innerHTML = '' +
        '<div class="col-12">' +
          '<div class="control-medium">' +
            '<label class="form-label small" for="field-version_dataset_title_dummy">' + self._('Title') + '</label>' +
            '<div class="controls">' +
              '<input id="field-version_dataset_title_dummy" type="text" name="version_dataset_title_dummy" class="form-control" data-version-field="title" />' +
            '</div>' +
          '</div>' +
        '</div>';

      var row3 = document.createElement('div');
      row3.className = 'row g-2';
      row3.innerHTML = '' +
        '<div class="col-12">' +
          '<div class="control-medium control-full">' +
            '<label class="form-label small" for="field-version_dataset_description_dummy">' + self._('Description') + '</label>' +
            '<div class="controls">' +
              '<textarea id="field-version_dataset_description_dummy" name="version_dataset_description_dummy" class="form-control" rows="3" data-version-field="description"></textarea>' +
            '</div>' +
          '</div>' +
        '</div>';

      wrapper.appendChild(row1);
      wrapper.appendChild(row2);
      wrapper.appendChild(row3);

      var inputUrl = wrapper.querySelector('#field-version_dataset_url_dummy');
      var inputTitle = wrapper.querySelector('#field-version_dataset_title_dummy');
      var inputDesc = wrapper.querySelector('#field-version_dataset_description_dummy');
      var fetchBtn = wrapper.querySelector('#version-dataset-fetch');

      var syncHidden = function () {
        var obj = {};
        var url = (inputUrl && inputUrl.value || '').trim();
        var title = (inputTitle && inputTitle.value || '').trim();
        var desc = (inputDesc && inputDesc.value || '').trim();
        if (url) obj.url = url;
        if (title) obj.title = title;
        if (desc) obj.description = desc;
        hidden.value = self._stringifyOrEmpty(obj);
        self._updateVersionTitleDisabled(inputUrl, inputTitle);
      };

      // Prefill from existing JSON
      var parsed = this._parseJsonSafe(hidden.value, null);
      if (parsed && typeof parsed === 'object') {
        if (inputUrl && parsed.url) inputUrl.value = parsed.url;
        if (inputTitle && parsed.title) inputTitle.value = parsed.title;
        if (inputDesc && parsed.description) inputDesc.value = parsed.description;
      }
      this._updateVersionTitleDisabled(inputUrl, inputTitle);

      [inputUrl, inputTitle, inputDesc].forEach(function (inp) {
        if (!inp) return;
        inp.addEventListener('input', syncHidden);
        inp.addEventListener('change', syncHidden);
      });

      if (fetchBtn && inputUrl) {
        fetchBtn.addEventListener('click', async function (e) {
          e.preventDefault();
          var url = (inputUrl.value || '').trim();
          if (!url) return;
          var meta = await self._fetchVersionMeta(url);
          if (meta) {
            if (inputTitle && meta.title) inputTitle.value = meta.title;
            if (inputDesc && meta.description) inputDesc.value = meta.description;
          }
          syncHidden();
        });
      }

      syncHidden();
    },

    _initDatasetVersions: function () {
      var wrapper = document.querySelector('[data-udc-dataset-versions-wrapper="true"]');
      var hidden = document.getElementById('field-dataset_versions');
      if (!wrapper || !hidden) return;

      var rowsContainer = wrapper.querySelector('.dataset-versions-rows');
      var addBtn = document.getElementById('dataset-versions-add');
      var self = this;

      var buildRow = function (data) {
        data = data || {};
        var rowIdx = rowsContainer.querySelectorAll('[data-version-row="true"]').length;
        var row = document.createElement('div');
        row.className = 'row g-2 align-items-end mb-1';
        row.setAttribute('data-version-row', 'true');
        row.setAttribute('data-version-row-id', String(rowIdx));
        row.innerHTML = '' +
          '<div class="col-md-8 col-lg-7">' +
            '<div class="control-medium">' +
              '<label class="form-label small" for="field-dataset_versions_url_dummy_' + rowIdx + '">' + self._('URL') + '</label>' +
              '<div class="controls">' +
                '<input type="text" class="form-control" data-version-field="url" id="field-dataset_versions_url_dummy_' + rowIdx + '" />' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<div class="col-md-2 col-lg-2 d-flex align-items-end">' +
            '<button type="button" class="btn btn-outline-primary w-100" data-version-fetch="true" data-udc-disable-on-load>' + self._('Auto-fill') + '</button>' +
          '</div>' +
          '<div class="col-md-2 col-lg-3 d-flex align-items-end">' +
            '<button type="button" class="btn btn-outline-danger w-100" data-version-remove="true">' + self._('Remove') + '</button>' +
          '</div>';

        var descRow = document.createElement('div');
        descRow.className = 'row mb-1';
        descRow.innerHTML = '' +
          '<div class="col-12">' +
            '<div class="form-groupcontrol-medium">' +
              '<label class="form-label small" for="field-dataset_versions_title_dummy_' + rowIdx + '">' + self._('Title') + '</label>' +
              '<div class="controls">' +
                '<input type="text" class="form-control" data-version-field="title" id="field-dataset_versions_title_dummy_' + rowIdx + '" />' +
              '</div>' +
            '</div>' +
          '</div>';

        var descRow2 = document.createElement('div');
        descRow2.className = 'row mb-3';
        descRow2.innerHTML = '' +
          '<div class="col-12">' +
            '<div class="control-medium control-full">' +
              '<label class="form-label small" for="field-dataset_versions_description_dummy_' + rowIdx + '">' + self._('Description (optional)') + '</label>' +
              '<div class="controls">' +
                '<textarea class="form-control" rows="3" data-version-field="description" id="field-dataset_versions_description_dummy_' + rowIdx + '"></textarea>' +
              '</div>' +
            '</div>' +
          '</div>';

        rowsContainer.appendChild(row);
        rowsContainer.appendChild(descRow);
        rowsContainer.appendChild(descRow2);

        var urlInput = row.querySelector('[data-version-field="url"]');
        var titleInput = descRow.querySelector('[data-version-field="title"]');
        var descInput = descRow2.querySelector('[data-version-field="description"]');
        var rowId = String(rowIdx);
        if (urlInput) urlInput.setAttribute('data-version-row-id', rowId);
        if (titleInput) titleInput.setAttribute('data-version-row-id', rowId);
        if (descInput) descInput.setAttribute('data-version-row-id', rowId);

        if (data.url) urlInput.value = data.url;
        if (data.title) titleInput.value = data.title;
        if (data.description) descInput.value = data.description;

        var updateTitleDisabled = function () {
          self._updateVersionTitleDisabled(urlInput, titleInput);
        };
        urlInput.addEventListener('input', updateTitleDisabled);
        urlInput.addEventListener('change', updateTitleDisabled);
        updateTitleDisabled();

        [urlInput, titleInput, descInput].forEach(function (inp) {
          inp.addEventListener('input', syncHidden);
          inp.addEventListener('change', syncHidden);
        });

        var fetchBtn = row.querySelector('[data-version-fetch="true"]');
        if (fetchBtn && urlInput) {
          fetchBtn.addEventListener('click', async function (e) {
            e.preventDefault();
            var url = (urlInput.value || '').trim();
            if (!url) return;
            var meta = await self._fetchVersionMeta(url);
            if (meta) {
              if (titleInput && meta.title) titleInput.value = meta.title;
              if (descInput && meta.description) descInput.value = meta.description;
            }
            syncHidden();
          });
        }

        var removeBtn = row.querySelector('[data-version-remove="true"]');
        if (removeBtn) {
          removeBtn.addEventListener('click', function (e) {
            e.preventDefault();
            row.parentNode.removeChild(row);
            descRow.parentNode.removeChild(descRow);
            descRow2.parentNode.removeChild(descRow2);
            syncHidden();
          });
        }
      };

      var syncHidden = function () {
        var rows = rowsContainer.querySelectorAll('[data-version-row="true"]');
        var out = [];
        rows.forEach(function (row) {
          var rowId = row.getAttribute('data-version-row-id');
          var urlInput = rowId ? rowsContainer.querySelector('[data-version-field="url"][data-version-row-id="' + rowId + '"]') : null;
          var titleInput = rowId ? rowsContainer.querySelector('[data-version-field="title"][data-version-row-id="' + rowId + '"]') : null;
          var descInput = rowId ? rowsContainer.querySelector('[data-version-field="description"][data-version-row-id="' + rowId + '"]') : null;
          var url = (urlInput && urlInput.value) || '';
          var title = (titleInput && titleInput.value) || '';
          var descVal = (descInput && descInput.value) || '';
          url = url.trim();
          title = title.trim();
          descVal = descVal.trim();
          if (!url && !title && !descVal) return;
          var obj = {};
          if (url) obj.url = url;
          if (title) obj.title = title;
          if (descVal) obj.description = descVal;
          out.push(obj);
        });
        hidden.value = self._stringifyOrEmpty(out);
      };

      // Prefill from hidden
      var existing = this._parseJsonSafe(hidden.value, []);
      if (Array.isArray(existing) && existing.length) {
        existing.forEach(function (item) { buildRow(item); });
      }

      if (addBtn) {
        addBtn.addEventListener('click', function (e) {
          e.preventDefault();
          buildRow({});
          syncHidden();
        });
      }

      // Ensure at least one row so the user has a place to type
      if (!rowsContainer.querySelector('[data-version-row="true"]')) {
        buildRow({});
      }

      syncHidden();
    },

    _unlockForm: function () {
      if (this._loadingOverlay) {
        this._loadingOverlay.classList.add('d-none');
        this._loadingOverlay.setAttribute('aria-hidden', 'true');
      }
      document.querySelectorAll('[data-udc-disable-on-load]').forEach(function (el) {
        if (el.dataset.udcLocked !== 'true') return;
        delete el.dataset.udcLocked;
        if (el.tagName === 'BUTTON' || el.tagName === 'INPUT') {
          el.removeAttribute('disabled');
        } else {
          el.classList.remove('disabled');
          if (el.dataset.udcOriginalAriaDisabled && el.dataset.udcOriginalAriaDisabled !== '__none__') {
            el.setAttribute('aria-disabled', el.dataset.udcOriginalAriaDisabled);
          } else {
            el.removeAttribute('aria-disabled');
          }
          if (el.dataset.udcOriginalTabindex && el.dataset.udcOriginalTabindex !== '__none__') {
            el.setAttribute('tabindex', el.dataset.udcOriginalTabindex);
          } else {
            el.removeAttribute('tabindex');
          }
          delete el.dataset.udcOriginalAriaDisabled;
          delete el.dataset.udcOriginalTabindex;
        }
      });
    },

    // ===== language toggles =====
    _initLangToggles: function () {
      var self = this;

      // per-field toggle buttons
      document.querySelectorAll('.udc-lang-toggle').forEach(function (grp) {
        grp.addEventListener('click', function (e) {
          var btn = e.target.closest('button[data-lang]');
          if (!btn) return;
          e.preventDefault();
          var lang = btn.getAttribute('data-lang');
          var forName = grp.getAttribute('data-i18n-for');
          self._applyLangToField(forName, lang);
          self._markActive(grp, lang);
        });
      });

      // level-wide toggle
      document.querySelectorAll('.udc-level-toggle').forEach(function (grp) {
        grp.addEventListener('click', function (e) {
          var btn = e.target.closest('button[data-lang]');
          if (!btn) return;
          e.preventDefault();
          var lang = btn.getAttribute('data-lang');
          var levelIdx = parseInt(grp.getAttribute('data-level-index'), 10);
          self._applyLangToLevel(levelIdx, lang);
          self._markActive(grp, lang);
        });
      });

      // set default active state on all toggle groups
      document.querySelectorAll('.udc-lang-toggle, .udc-level-toggle').forEach(function (grp) {
        var lang = self.currentLang;
        self._markActive(grp, lang);
      });
    },

    _markActive: function (groupEl, lang) {
      groupEl.querySelectorAll('button[data-lang]').forEach(function (b) {
        var isOn = b.getAttribute('data-lang') === lang;
        b.classList.toggle('btn-primary', isOn);
        b.classList.toggle('active', isOn);
        b.classList.toggle('btn-outline-secondary', !isOn);
      });
    },

    _applyLangToLevel: function (levelIdx, lang) {
      var self = this;
      this.currentLang = lang;
      var level = (this.pkgConfig || [])[levelIdx] || {};
      (level.fields || []).forEach(function (f) {
        if (f && f.type === 'text' && f.name) self._applyLangToField(f.name, lang);
        if (f && f.ckanField === 'title') self._applyLangToField('title', lang);
        if (f && f.ckanField === 'description') self._applyLangToField('notes', lang);
      });

      // also flip all per-field toggle groups in this level
      document.querySelectorAll('.udc-lang-toggle[data-level-index="' + levelIdx + '"]').forEach(function (grp) {
        self._markActive(grp, lang);
      });

      self._applyLangToField('title', lang);
      self._applyLangToField('notes', lang);
      self._applyLangToField('tags', lang);
    },

    _applyLangToField: function (forName, lang) {
      if (!forName) return;
      var groupInputs = document.querySelectorAll('.udc-i18n-input[data-i18n-for="' + forName + '"]');
      if (!groupInputs.length) return;
      groupInputs.forEach(function (inp) {
        var L = inp.getAttribute('data-lang');
        var wrap = inp.closest('[data-udc-i18n-wrapper="true"]') || inp.closest('.control-group, .form-group') || inp.parentElement;
        if (!wrap) return;
        wrap.classList.toggle('d-none', L !== lang);
      });
    },

    // ===== multiple selects =====
    _initMultipleSelects: function () {
      var self = this;
      (this.pkgConfig || []).forEach(function (level) {
        (level.fields || []).forEach(function (field) {
          if (field && field.type === 'multiple_select' && field.name) {
            var ele = document.querySelector('#field-' + field.name);
            if (!ele) return;
            var options = []; var selectedOptions = [];
            var currStr = ele.getAttribute('value') || '';
            var curr = currStr ? currStr.split(',') : [];

            (field.options || []).forEach(function (opt) {
              var label = (typeof opt.text === 'string')
                ? opt.text
                : (opt.text && (opt.text[self.currentLang] || opt.text[self.defaultLang] || opt.text[self.langs[0]] || Object.values(opt.text)[0])) || opt.value;
              options.push({ value: opt.value, label: label });
              if (curr.indexOf(opt.value) !== -1) selectedOptions.push(opt.value);
            });

            VirtualSelect.init({
              ele: '#field-' + field.name,
              options: options,
              search: true, multiple: true, showValueAsTags: true,
              selectedValue: selectedOptions, maxWidth: '100%', allowNewOption: !!field.allowNewOption
            });
          }
        });
      });
    },

    // ===== progress =====
    _initProgressTracking: function () {
      this.levels = [];
      this.tabs = [];

      for (var i = 0; i < this.pkgConfig.length; i++) {
        this.tabs.push(document.querySelector('#maturity_level_' + (i + 1) + '-tab'));
        var level = this.pkgConfig[i];
        var entry = { fieldElements: [], progressElement: document.querySelector('#progress-' + (i + 1)) };

        (level.fields || []).forEach(function (field) {
          if (field.name) {
            var el = document.querySelector('#field-' + field.name);
            if (el) { el.addEventListener('change', this._onFieldChange.bind(this)); entry.fieldElements.push(el); }
          } else if (field.ckanField) {
            if (field.ckanField === 'custom_fields') return;
            if (field.ckanField === 'organization_and_visibility') {
              var org = document.querySelector('#field-organizations');
              var vis = document.querySelector('#field-private');
              if (org) { entry.fieldElements.push(org); org.addEventListener('change', this._onFieldChange.bind(this)); }
              if (vis) { entry.fieldElements.push(vis); vis.addEventListener('change', this._onFieldChange.bind(this)); }
            } else {
              var cel = document.querySelector('#field-' + field.ckanField);
              if (cel) { entry.fieldElements.push(cel); cel.addEventListener('change', this._onFieldChange.bind(this)); }
            }
          }
        }, this);

        this.levels[i] = entry;
      }
      this._onFieldChange();
    },

    _onFieldChange: function () {
      for (var i = 0; i < this.levels.length; i++) {
        var fe = this.levels[i].fieldElements;
        var bar = this.levels[i].progressElement;
        var filled = 0;
        for (var j = 0; j < fe.length; j++) {
          var el = fe[j];
          if (el && el.value != null && el.value !== '') filled++;
        }
        var pct = Math.round((filled / (fe.length || 1)) * 100);
        if (bar) { bar.innerHTML = pct + '%'; bar.style = 'width: ' + pct + '%'; }
        if (this.tabs[i]) this.tabs[i].innerHTML = this._('Maturity Level') + ' ' + (i + 1) + ' (' + pct + '%)';
      }
    }
  };
});
