**Project Overview**
- ckanext-udc bundles `udc`, `udc_theme`, `udc_import`, `udc_import_other_portals`, and `udc_react`; start with `ckanext/udc/plugin.py` to see every CKAN hook implementation.
- Runtime maturity model and ontology preload definitions live in `ckanext/udc/config.example.json`, but live values are written to `ckan.model.system_info` under `ckanext.udc.config`.
- Chained helpers/actions in `ckanext/udc/helpers.py` rename catalogue UX strings, reload plugin config after admin saves, and fan out to external systems.

**Runtime & Config**
- Key `ckan.ini` entries: `udc.sparql.*`, `udc.multilingual.languages`, and `ckanext.udc.desc.config` (JSON) — set them before enabling GraphDB or OpenAI features.
- Run `ckan -c /etc/ckan/default/ckan.ini udc initdb` after plugging in new tables; the CLI path short-circuits graph sync for non-web contexts.
- Saving the Settings page triggers `config_option_update`, which calls `UdcPlugin.reload_config`; keep JSON schema backward compatible with `config.example.json`.

**Backend Patterns**
- `UdcPlugin` extends `DefaultDatasetForm` and rewires schemas via `_modify_package_schema`; multilingual text fields use validators in `ckanext/udc/i18n.py` to persist JSON blobs in extras.
- Multilingual fields (`title_translated`, `notes_translated`, etc.) are stored as JSON in package extras; core fields are **NOT** automatically synced - use `pick_locale_with_fallback()` helper in templates for language fallback with visual indicators.
- `udc_seed_translated_from_core()` seeds to **user's current locale** (`h.lang()`), not system default; `udc_lang_object()` preserves explicit empty values and does not auto-seed between languages.
- `package_update` and `package_delete` hooks dispatch to `graph.logic.onUpdateCatalogue`/`onDeleteCatalogue`; raise `logic.ValidationError` on failures so UI surfaces graph errors.
- Register additional logic through toolkit actions (eg. `license_*`, `file_format_*`, `summary_*`, `deleted_users_list`, `purge_deleted_users`) instead of direct imports to respect CKAN permission checks.

**Search & Solr**
- `/catalogue` blueprint in `ckanext/udc/views.py` parses `fts_`, `exact_`, `min_`, and `max_` query params and rebuilds URLs with `remove_field` helpers.
- `ckanext/udc/solr/index.py` injects `<field>_<lang>_{txt|f}` properties before indexing; update your Solr schema when adding maturity-model fields.
- `filter_facets_get` returns stable keys (e.g., `extras_file_format`) while mapping to language-specific Solr fields and localizing dropdown labels from `UdcPlugin.dropdown_options`.
- Language fallback: `pick_locale_with_fallback(texts, lang)` returns `(value, fallback_lang)` tuple; use in templates to show "(showing value for Français)" when user's language unavailable.

**User Management**
- `deleted_users_list` action lists all soft-deleted users (state='deleted'); sysadmin-only access via `ckanext/udc/user/auth.py`.
- `purge_deleted_users` action permanently removes deleted users and cleans up memberships/collaborations; **cannot be undone**, sysadmin-only.
- User management APIs documented in `docs/API_USER_MANAGEMENT.md`; see `ckanext/udc/tests/test_user_actions.py` for test patterns.

**Graph & External Services**
- Knowledge graph sync depends on a reachable SPARQL endpoint; `reload_config` applies ontology preloads and `graph/logic.py` emits delete/insert SPARQL per package change.
- AI summaries in `ckanext/udc/desc/actions.py` call OpenAI; populate `ckanext.udc.desc.config` with `openai_key`, `openai_model`, and token limits before triggering `summary_generate`.
- System management endpoints in `ckanext/udc/system/actions.py` expect sysadmin context; keep new admin actions consistent with existing access patterns.

**React Frontend**
- Frontend lives in `ckanext/udc_react/ckan-udc-react` (Vite); run `npm install`, `npm run dev -- --host 0.0.0.0` for hot reload, and `npm run build` to refresh `public` assets.
- Start CKAN with `VITE_ORIGIN=http://<host>:5173` when developing; production builds rely on the compiled assets bundled via `ckanext.udc_react`.
- React components consume the maturity model schema and `filter_facets_get` payloads, so keep API field names stable when updating backend logic.

**CLI & Ops**
- Use `ckan udc move-to-catalogues` to retag legacy datasets, then run `ckan -c /etc/ckan/default/ckan.ini search-index rebuild` to refresh Solr.
- uwsgi is expected to run with gevent and websocket support (see README); rebuild uwsgi with SSL and update nginx when enabling realtime features.
- Background jobs run via `ckan -c /etc/ckan/default/ckan.ini jobs worker`; set `WERKZEUG_DEBUG_PIN` if you need interactive debugging.

**Testing & QA**
- Execute backend tests with `pytest --ckan-ini=test.ini` or use docker-compose: `docker-compose run ckan-test`; leverage `pytest-ckan` fixtures (`clean_db`, `with_plugins`, `app`) when expanding `ckanext/udc/tests`.
- Test organization: Core tests in `ckanext/udc/tests/` (helpers, package actions, plugin, solr config, user actions); graph transformation tests in `ckanext/udc/tests/graph/` - see respective README.md files.
- User management tests demonstrate authorization patterns, multilingual persistence, and integration scenarios - follow similar patterns for new features.
- Linting/formatting rules are centralized in `setup.cfg` and `pyproject.toml`; mirror those when adding new packages or scripts.
- After touching multilingual fields or Solr mappings, reindex (`ckan -c /etc/ckan/default/ckan.ini search-index rebuild`) to validate schema compatibility early.
- Docker services use internal ports (db:5432, solr:8983, redis:6379) for inter-container communication; external ports (5433, 8984, 6380) are for host access only.

**Key Implementation Details**
- JavaScript form handling (`package.js`): `_collectI18nValues()` includes empty strings to signal intentional field clearing to backend validators.
- Template helpers: Use `render_multilingual_value()` and `render_multilingual_tags()` macros in `additional_info.html` to reduce duplication and show language fallback indicators.
- Empty value handling: Empty strings, whitespace-only strings, and empty arrays treated as missing values in fallback logic (`is_non_empty()` helper).
- Package actions pass **result dict** to graph functions, not input data_dict - tests validate this flow.

