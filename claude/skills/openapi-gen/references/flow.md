# OpenAPI Generator Flow

Scan project API endpoints and generate/update OpenAPI 3.x YAML with validation.

---

## Input Parameters

From `$ARGUMENTS`:

- `path` (optional): Filter routes by path prefix (e.g. "/api/v1")
- `output` (optional): Output file path (default: `openapi.yaml` in project root)
- `framework` (optional): Force framework type (skip auto-detection)
- `max_routes` (optional): Safety limit on number of routes to process (default: 500). If exceeded, ask user to narrow scope with `path` filter.

---

## Execution Flow

### 1. Framework Detection

If `$ARGUMENTS` includes `framework`, skip detection and use the specified value.

Otherwise, auto-detect by scanning manifest files in project root:

#### 1.1 Detection Procedure

```
1. Glob for manifest files: composer.json, package.json, requirements.txt, pyproject.toml, pom.xml, build.gradle, Gemfile
2. For each found manifest, Grep for framework indicators (see table below)
3. Collect all matches into a candidates list
4. If exactly 1 candidate → use it
5. If 0 candidates → ask user: "No framework detected. Which framework does this project use?"
6. If 2+ candidates → ask user: "Multiple frameworks detected: [list]. Which one contains the API endpoints?"
```

#### 1.2 Framework Indicator Table

| Manifest           | Grep Pattern                     | Framework       | Route Files                                      |
| ------------------ | -------------------------------- | --------------- | ------------------------------------------------ |
| `composer.json`    | `"laravel/framework"`            | Laravel         | `routes/api.php`, `routes/web.php`               |
| `package.json`     | `"express"` in dependencies      | Express         | `app.js`, `index.js`, `server.js`, `src/routes/` |
| `package.json`     | `"@nestjs/core"`                 | NestJS          | `src/**/*.controller.ts`                         |
| `package.json`     | `"next"` in dependencies         | Next.js         | `pages/api/`, `app/api/`                         |
| `requirements.txt` | `fastapi`                        | FastAPI         | `main.py`, `app/`, `routers/`                    |
| `requirements.txt` | `flask`                          | Flask           | `app.py`, `views.py`                             |
| `requirements.txt` | `django`                         | Django          | `urls.py`, `views.py`                            |
| `pyproject.toml`   | `fastapi` or `flask` or `django` | (same as above) | (same as above)                                  |
| `pom.xml`          | `spring-boot`                    | Spring Boot     | `src/**/*Controller.java`                        |
| `build.gradle`     | `spring-boot`                    | Spring Boot     | `src/**/*Controller.java`                        |
| `Gemfile`          | `'rails'`                        | Rails           | `config/routes.rb`                               |

#### 1.3 Output

After detection, display:

```
Framework detected: {framework}
Route files to scan: {list of route files}
Proceeding with {framework} extractor...
```

### 1.5 Existing Spec Detection (Incremental Mode)

After framework detection, check if a valid OpenAPI spec already exists in the project.

#### 1.5.1 Detection Procedure

```
1. Glob for existing spec files: **/openapi*.{yaml,yml,json}, **/api-spec*.{yaml,yml,json}, **/swagger*.{yaml,yml,json}
2. For each candidate, verify it contains `openapi:` (YAML) or `"openapi"` (JSON) at top level
3. If found: enter Incremental Mode
4. If not found: enter Full Generation Mode (original flow, skip to Step 2)
```

#### 1.5.2 Incremental Mode Decision

When a valid spec file is found:

```
Existing OpenAPI spec found: {file_path} ({line_count} lines, {path_count} paths)
→ Entering Incremental Mode: will diff against current routes and patch.
```

#### 1.5.3 Incremental Mode Flow

**Replace Steps 2–4 with the following:**

**Step A: Extract current routes** (same as Step 2, but output is a route list only — no schema building yet)

Run the framework-specific Route Extraction (Step 2.1) to produce a list of:

```
{ method, path, controller, middleware }
```

**Step B: Parse existing spec paths**

Read the existing spec file and extract all defined paths + methods:

```
{ method, path, operationId }
```

**Step C: Diff routes vs spec**

Compare the two lists and classify each route:

| Category      | Condition                                               | Action                                                                                                     |
| ------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Missing**   | Route exists in code but not in spec                    | Add new path entry (use Step 3 schema building for this route only)                                        |
| **Removed**   | Path exists in spec but not in code                     | Mark with `x-deprecated: true` and `description` note; do NOT delete (user may have intentionally kept it) |
| **Changed**   | Route exists in both, but controller/middleware differs | Update `security`, `x-source-file`; preserve existing `summary`, `description`, `requestBody`, `responses` |
| **Unchanged** | Route matches exactly                                   | Skip — do not touch                                                                                        |

**Step D: Schema drift check**

For each **Unchanged** route, optionally verify schema accuracy:

1. Read the controller method
2. Compare response fields against the spec's response schema
3. If new fields found in code but missing in spec → add them
4. If fields removed from code but present in spec → add `x-deprecated: true` to those properties
5. If field names/types changed → update and add a `# updated by openapi-gen` comment

Only perform this check when:

- The controller file's modification time is newer than the spec file, OR
- The user explicitly requests `--full-check`

**Step E: Apply patches**

Use the Edit tool to apply changes to the existing spec file:

- Insert new path entries in alphabetical order within the `paths:` section
- Update changed entries in-place
- Add missing `components/schemas` if new endpoints reference them
- Preserve all existing formatting, comments, and manually-written descriptions

**Step F: Report diff summary**

```
Incremental update complete:
- Added: {count} new endpoints
- Updated: {count} endpoints (schema/middleware changes)
- Deprecated: {count} endpoints (in spec but not in routes)
- Unchanged: {count} endpoints (skipped)
```

Then proceed to Step 5 (Validation).

### 2. Route Extraction

Use a two-strategy approach (static analysis first, reflection fallback):

#### 2.1 Static Code Analysis (Primary)

Analyze route definition files using Glob/Grep/Read tools.

##### Laravel Extractor

**Step 1: Find route files**

```
Glob: routes/*.php
```

**Step 2: Extract route definitions**

Grep each route file for these patterns:

```
Route::(get|post|put|patch|delete|options)\s*\(
Route::(resource|apiResource)\s*\(
Route::group\s*\(
Route::prefix\s*\(
Route::middleware\s*\(
```

**Step 3: Parse each route match**

For each `Route::{method}('{path}', ...)` match:

- Extract HTTP method from the `Route::` call
- Extract path string (first argument)
- Extract controller reference: `[Controller::class, 'method']` or `'Controller@method'`
- Convert Laravel path params `{id}` to OpenAPI `{id}` (same format)
- Track enclosing `Route::group` / `Route::prefix` for path prefixes
- Track `Route::middleware` for auth/throttle detection

For `Route::apiResource('{name}', Controller::class)`, expand to standard CRUD:

- GET `/{name}` → index
- POST `/{name}` → store
- GET `/{name}/{singular}` → show (where `{singular}` is the singular form of `{name}`, e.g. `users` → `{user}`)
- PUT/PATCH `/{name}/{singular}` → update
- DELETE `/{name}/{singular}` → destroy

For `Route::resource('{name}', Controller::class)`, additionally include:

- GET `/{name}/create` → create
- GET `/{name}/{singular}/edit` → edit

**Step 4: Read Controllers**

For each controller reference found:

- Glob for the controller file: `app/Http/Controllers/**/{ControllerName}.php`
- Read the target method
- Extract: docblock comments, FormRequest type hints, return type hints
- Detect `$request->validate([...])` rules for request schema

##### Express Extractor

**Step 1: Find route files**

```
Glob: {app,index,server}.{js,ts} src/routes/**/*.{js,ts} routes/**/*.{js,ts}
```

**Step 2: Extract route definitions**

Grep for these patterns:

```
(app|router)\.(get|post|put|patch|delete)\s*\(
app\.use\s*\(\s*['"]
router\.(route)\s*\(
```

**Step 3: Parse each route match**

For each `app.get('/path', handler)` or `router.post('/path', ...)`:

- Extract HTTP method from the method call
- Extract path string (first argument)
- Convert Express path params `:id` to OpenAPI `{id}`
- Track `app.use('/prefix', router)` for path prefix mounting
- Detect middleware: `passport.authenticate`, `auth`, `isAuthenticated`

**Step 4: Read Handlers**

For each handler function:

- Read the function body
- Grep for `req.params.{name}` → path parameters
- Grep for `req.query.{name}` → query parameters
- Grep for `req.body.{name}` or `req.body` destructuring → request body fields
- Grep for `res.json(...)` or `res.send(...)` → response shape hints

##### Other Frameworks

For unsupported frameworks, fall back to a generic approach:

1. Ask the user: "Route files not auto-detected for {framework}. Please specify the route file paths."
2. Read the specified files
3. Apply best-effort pattern matching for HTTP method + path combinations
4. Mark all extracted routes with `confidence: low`

##### Route Data Structure

For each discovered route, produce:

```yaml
- method: GET|POST|PUT|PATCH|DELETE
  path: /api/users/{id}
  controller: UserController@show
  middleware: [auth:sanctum]
  description: "from docblock or TODO: add description"
  params:
    path: [{ name: id, type: integer }]
    query: []
    body: null
  response_hint: "Resource|Collection|JsonResponse|unknown"
  source_file: app/Http/Controllers/UserController.php
  source_line: 42
```

#### 2.1.1 Route Count Safety Check

After static extraction completes, check route count against `max_routes` (default: 500):

- If count <= `max_routes` → proceed normally
- If count > `max_routes` → ask user: "Discovered {count} routes (limit: {max_routes}). Please narrow scope with `path` filter, or increase `max_routes` to continue."

#### 2.2 Framework Reflection (Fallback)

If static analysis yields incomplete results and runtime is available:

**Laravel** (via podman exec):

```
podman exec -w /var/www/html/php/{project} php-fpm php artisan route:list --json
```

**Express**: No built-in reflection. Stay with static analysis.

Reflection results are merged with static analysis (reflection fills gaps, static provides code context).

### 3. Schema Building

For each route in the extracted route list, build request/response schemas.

#### 3.1 Request Schema

**Path Parameters**:

For each `{param}` in the route path:

- Default type: `string`
- If param name contains `id` or route is a show/update/delete action → type: `integer`
- Add `required: true` (path params are always required in OpenAPI)

**Query Parameters** (GET/DELETE methods):

- **Laravel**: Read controller method, grep for `$request->query('name')`, `$request->input('name')`, `$request->get('name')`
- **Express**: Grep handler for `req.query.name` or `req.query['name']`
- For index/list endpoints, add common defaults: `page` (integer), `per_page` (integer) if pagination patterns detected
- All query params default to `required: false`

**Request Body** (POST/PUT/PATCH methods):

- **Laravel**: Look for FormRequest type hint in controller method → read the FormRequest's `rules()` method → map Laravel validation rules to OpenAPI types:
  - `required` → required field
  - `string` → type: string
  - `integer`/`numeric` → type: integer/number
  - `email` → type: string, format: email
  - `array` → type: array
  - `boolean` → type: boolean
  - `date` → type: string, format: date
  - `nullable` → nullable: true
  - If no FormRequest, grep for `$request->validate([...])` inline rules
- **Express**: Grep for `req.body.field` or destructured `const { field } = req.body` → infer field names (types default to string with `TODO: specify type`)

If no request body can be inferred → omit `requestBody` (don't generate empty schemas)

#### 3.2 Response Schema

- **Laravel**: Check return type/statement:
  - `return new XxxResource(...)` → grep XxxResource's `toArray()` for field list
  - `return XxxResource::collection(...)` → wrap in array
  - `return response()->json([...])` → infer from literal keys
  - Otherwise → `TODO: specify response schema`
- **Express**: Check `res.json({...})` or `res.status(N).json({...})` → infer from literal keys
- If uncertain → use generic placeholder schema

**Default Response Codes** (auto-added based on context):

| Context                              | Status Codes                                            |
| ------------------------------------ | ------------------------------------------------------- |
| All endpoints                        | `200` (or `201` for POST)                               |
| Auth middleware present              | `401 Unauthorized`                                      |
| show/update/delete (single resource) | `404 Not Found`                                         |
| POST/PUT with validation             | `422 Unprocessable Entity`                              |
| All endpoints                        | `500 Internal Server Error` (optional, omit if minimal) |

### 4. OpenAPI YAML Generation

#### 4.1 Document Structure

Generate the OpenAPI document using the Write tool. The structure:

```yaml
openapi: 3.0.3
info:
  title: "{Project Name} API"
  version: "1.0.0"
  description: "Auto-generated by openapi-gen skill"
  x-generator: "claude-code-openapi-gen"
  x-generated-at: "{ISO timestamp}"
servers:
  - url: "http://localhost"
    description: "Local development"
tags: [] # populated from route groups/prefixes
paths: {} # populated from extracted routes
components:
  schemas: {} # populated from inferred schemas
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

#### 4.2 Path Generation Rules

For each extracted route, generate a path item:

1. **operationId**: derive from controller method — `{ControllerName}_{method}` (e.g. `UserController_index`). Must be unique across the document.
2. **summary**: from docblock first line, or `"TODO: add summary for {controller}@{method}"`
3. **tags**: from route prefix (e.g. `/api/users/*` → tag: `Users`)
4. **parameters**: from Schema Building step 3.1
5. **requestBody**: from Schema Building step 3.1 (POST/PUT/PATCH only, omit if empty)
6. **responses**: from Schema Building step 3.2 + default status codes
7. **security**: if auth middleware detected → `[{bearerAuth: []}]`
8. **x-source-file**: source file path (for future incremental updates)
9. **x-source-hash**: SHA-256 of source file content (for change detection)

#### 4.3 Component Schema Deduplication

If multiple endpoints reference the same resource (e.g. `UserResource`):

- Extract to `components/schemas/User`
- Reference via `$ref: '#/components/schemas/User'` in path responses
- Avoid duplicating the same schema across multiple paths

#### 4.4 Tags Generation

Derive tags from route path prefixes:

- `/api/users/*` → `Users`
- `/api/orders/*` → `Orders`
- Capitalize first letter, strip plural if obvious

#### 4.5 Output

Write the assembled YAML to the output path (default: `openapi.yaml` in project root) using the Write tool.

### 5. Validation

#### 5.1 Dependency Check

Check if `@redocly/cli` is available:

```
Bash: npx @redocly/cli --version 2>/dev/null
```

If exit code != 0, prompt user:

```
Redocly CLI not found.
A) Install globally: npm install -g @redocly/cli
B) Install locally: npm install --save-dev @redocly/cli
C) Skip validation (not recommended)
```

If user chooses A or B, run the install command, then re-check.
If user chooses C, skip to Section 6 (Output) with a warning.

#### 5.2 Lint

Run validation:

```
Bash: npx @redocly/cli lint {output_path} --format stylish 2>&1
```

#### 5.3 Handle Results

**Exit code 0 (no errors)**:

- Report: "Validation passed. OpenAPI document is valid."

**Exit code 0 with warnings**:

- Display warnings to user
- Report: "Validation passed with {N} warnings."

**Exit code 1 (errors)**:

- Parse error output for common fixable issues:

| Error Pattern                             | Auto-Fix Action                                       |
| ----------------------------------------- | ----------------------------------------------------- |
| `Operation object should contain summary` | Add `summary: "TODO: add summary"`                    |
| `Must have a non-empty description`       | Add `description: "TODO: add description"`            |
| `Invalid reference` / `$ref not found`    | Remove the broken `$ref`, inline a placeholder schema |
| `Duplicate operationId`                   | Append numeric suffix to make unique                  |
| `Missing required field` in schema        | Add the field with `TODO` placeholder                 |

- Apply fixes to the YAML file using Edit tool
- Re-run lint (max 1 retry)
- If still failing after retry, show remaining errors to user:

```
Validation failed with {N} errors after auto-fix attempt.
Remaining issues require manual attention:
- {error 1}
- {error 2}
```

#### 5.4 Validation Summary

```
Validation: {PASS|PASS_WITH_WARNINGS|FAIL}
Errors: {count}
Warnings: {count}
Auto-fixed: {count} issues
```

### 6. Output

**Full Generation Mode:**

```
OpenAPI document generated:
- File: {output_path}
- Framework: {detected_framework}
- Endpoints: {count} discovered
- Validation: {pass/fail with details}
- TODO markers: {count} fields need manual completion

Next steps:
- Review TODO markers and add descriptions/schemas
- Run: npx @redocly/cli lint {output_path}
```

**Incremental Mode:**

```
OpenAPI document updated:
- File: {output_path}
- Framework: {detected_framework}
- Added: {count} new endpoints
- Updated: {count} endpoints
- Deprecated: {count} endpoints
- Unchanged: {count} endpoints
- Validation: {pass/fail with details}

Next steps:
- Review added/updated endpoints for accuracy
- Run: npx @redocly/cli lint {output_path}
```

---

## Principles

1. **Static-first**: Prioritize code analysis over runtime reflection
2. **Conservative inference**: Use TODO placeholders for uncertain fields
3. **Framework isolation**: Each framework extractor is a self-contained section
4. **Non-destructive**: Never modify project source code
5. **Validate always**: Every generated file must pass redocly lint
6. **Preserve manual work**: In Incremental Mode, never overwrite existing summaries, descriptions, or manually-crafted schemas — only add missing pieces and update structural changes
