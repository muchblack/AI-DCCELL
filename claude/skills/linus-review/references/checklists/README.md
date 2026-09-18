# Language Checklists

Source: [alibaba/open-code-review](https://github.com/alibaba/open-code-review), `internal/config/rules/rule_docs/`, licensed under Apache License 2.0. Files here are unmodified vendor copies — see `NOTICE.md` for attribution.

52 checklists total, one per language/framework/config type. `flow.md` Step 1.6 only wires up a subset by file-extension mapping — the rest sit here inert until activated.

## Currently wired into `flow.md` (active)

| Checklist | Extensions |
|---|---|
| `php.md` | `.php`, `.phtml` |
| `python.md` | `.py`, `.pyi`, `.ipynb` |
| `java.md` | `.java` |
| `ts_js_tsx_jsx.md` | `.ts`, `.js`, `.tsx`, `.jsx`, `.mjs`, `.cjs` |
| `default.md` | fallback for any extension not matched above |

## Standby (downloaded, not yet wired)

Everything else: `arkts`, `astro`, `bicep`, `build_gradle`, `c`, `capnp`, `cargo_toml`, `composer_json`, `cpp`, `elm`, `freemarker`, `github_config`, `github_workflows`, `go`, `graphql`, `handlebars_mustache`, `haskell`, `json`, `jsonnet`, `julia`, `kotlin`, `mapper_dao_xml`, `matlab`, `nim`, `nix`, `objc`, `ocaml`, `package_json`, `po`, `pom_xml`, `pot`, `prisma`, `properties`, `protobuf`, `pug`, `r`, `rego`, `rust`, `solidity`, `swift`, `terraform`, `thrift`, `verilog`, `vhdl`, `vyper`, `yaml`, `zig`.

To activate one: add a row to the extension-mapping table in `references/flow.md` Step 1.6 and to the "Currently wired" table above. No other change needed.
