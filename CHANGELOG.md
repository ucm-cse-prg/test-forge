# CHANGELOG


## v0.0.0 (2025-04-22)

### Build System

- Updated project name
  ([`4adeb44`](https://github.com/ucm-cse-prg/test-forge/commit/4adeb44772ddb7d6a9289b031d99788d1f7a34a4))

### Continuous Integration

- Change runner to arc-runner-k8s
  ([`8163015`](https://github.com/ucm-cse-prg/test-forge/commit/81630152d02db64ef0ae1a54397fde98719b3bae))

- Converted token job into steps
  ([`76ee09e`](https://github.com/ucm-cse-prg/test-forge/commit/76ee09e86b666d7ad155e932cf97a8351cd30721))

By default `actions/create-github-app-token@v1` revokes tokens at the end of the job, so instead the
  action was copied into each job as a step

- Fixed typo in private-key secret name
  ([`06d275c`](https://github.com/ucm-cse-prg/test-forge/commit/06d275c0fc9cb0373c12ee82321e8480dd3da3ce))

- Fixed typo in token value
  ([`bcea995`](https://github.com/ucm-cse-prg/test-forge/commit/bcea99551fc8717ff2b53d18d64237755ce74cd8))

- Replaced GITHUB_TOKEN with app generated token
  ([`c857dc0`](https://github.com/ucm-cse-prg/test-forge/commit/c857dc094e12568274740fd86d5fe1d0e1786faa))

- Testing ruleset against checkout with token
  ([`e71d5e4`](https://github.com/ucm-cse-prg/test-forge/commit/e71d5e47a4f067e9b1537af4315d6addb48ba445))

- Updated python-semantic-release/publish-action version to "main"
  ([`543d39f`](https://github.com/ucm-cse-prg/test-forge/commit/543d39fb72edebb64e8853aae862731fed1bc3f9))

### Documentation

- Updated copilot commit instructions
  ([`d543154`](https://github.com/ucm-cse-prg/test-forge/commit/d543154c37863919477b7343aab1d89f80162cf0))
