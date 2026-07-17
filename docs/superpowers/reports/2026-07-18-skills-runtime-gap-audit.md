# M7A Skills Runtime Gap Audit

This is a read-only inventory of local AI Drama skill packages, archives, duplicate candidates, and current Runtime/Web integration evidence. It records metadata only: paths, versions, hashes, structure, manifest fields, tests, and registry references.

## Executive Answers

- `1_latest_bundle_version`: `v0.6`
- `2_latest_bundle_path`: `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/05-release/ai-drama-skills-v0.6.zip`
- `3_latest_workflow_orchestrator_version`: `v0.6`
- `4_latest_script_adaptation_skill_version`: `v0.6.1-rc2.4`
- `5_latest_storyboard_skill_version`: `v0.6`
- `6_runtime_registered_skill_count`: `3`
- `7_bundle_skills_not_in_runtime`: `10`
- `8_agent_orchestrator_in_chain`: `NEWER_LOCAL_NOT_IN_RUNTIME`
- `9_m7a_source_baseline`: `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/05-release/ai-drama-skills-v0.6.zip`
- `10_archive_candidates`: `10`

## Gap Matrix

| Skill | Latest source version | Runtime current version | Registered | Web integrated | Agent schedulable | Gate mapped | Test status | M7A action |
|---|---:|---:|---:|---:|---:|---:|---|---|
| ai-drama-character-bible-skill | v0.6 | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| ai-drama-image-prompt-skill | v0.6 | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| ai-drama-libtv-cli-execution-skill | v0.6 | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| ai-drama-project-setup-skill | v0.6 | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| ai-drama-prop-bible-skill | v0.6 | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| ai-drama-scene-bible-skill | v0.6 | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| ai-drama-scene-stabilization-skill | v0.6 | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| ai-drama-script-adaptation-skill | v0.6.1-rc2.4 | v0.6.1-rc2.4 | yes | yes | yes | yes | tests/test_manifest.py, tests/test_cli.py, tests/test_web_script_runtime.py, tests/web/test_script_workflow_api.py | Use as current runtime baseline. |
| ai-drama-series-canon-extraction-skill | v0.6 | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| ai-drama-shot-prompt-skill | v0.6 | v0.1.0 | yes | yes | yes | yes | tests/test_shot_prompt_skill_package.py, tests/web/test_shot_prompt_api.py, tools/verify_m2_assets_shot_prompts.py | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.6 | v0.2.1 | yes | yes | yes | yes | tests/test_storyboard_canonical_workflow.py, tests/web/test_storyboard_workflow_api.py, tools/verify_storyboard_workflow.py | Use as current runtime baseline. |
| ai-drama-visual-anchor-skill | v0.6 | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| ai-drama-workflow-orchestrator-skill | v0.6 | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| material extraction | not-found | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| video QC | not-found | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |
| video execution | not-found | not-registered | no | no | no | no | not found | Compare against canonical source before M7A integration. |

## Runtime Evidence

- `ai-drama-script-adaptation-skill@v0.6.1-rc2.4` registered at `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4` with hash `b38eae160957484c68b7d47973a8b45419266d33c83b35de91be7291679d845f`.
- `ai-drama-shot-prompt-skill@v0.1.0` registered at `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime/skills/ai-drama-shot-prompt-skill/v0.1.0` with hash `dd153d40bdded6fd60342eb0c67410d788209c979e66b74fffd4bf29d33de582`.
- `ai-drama-storyboard-design-skill@v0.1.0` registered at `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.1.0` with hash `347b27cfeb0b08c7d1acf825daacd6723f194d933ed34c0bdd18d821f3478230`.
- `ai-drama-storyboard-design-skill@v0.2.0` registered at `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.2.0` with hash `ce82543d7ebca9a976b99fb7829977c17ec53f07085ce1e6ae3c863a9d7447be`.
- `ai-drama-storyboard-design-skill@v0.2.1` registered at `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.2.1` with hash `e9d5524de3be6b9e2d83e3a869f7068c6d44096f6541537fa6913024bd1da303`.

## Web Runtime References

- `script_web` -> `ai-drama-script-adaptation-skill@v0.6.1-rc2.4`
- `storyboard_web` -> `ai-drama-storyboard-design-skill@v0.2.1`
- `storyboard_web_fallback` -> `ai-drama-storyboard-design-skill@v0.2.0`
- `shot_prompt_web` -> `ai-drama-shot-prompt-skill@v0.1.0`

## Bundle Candidates

- `unknown` `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime` status `INCOMPLETE_RELEASE` skills `5` hash `24ad5c27e3a5f17ecab0f962dca2190b981f6fd0f666e05e443b3a66a7c0ad7d`
- `unknown` `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime` status `INCOMPLETE_RELEASE` skills `5` hash `dc0826ff3b8fcfe556a51470edd3d8a0df4d684e9316d45d226c6fe06af19aaf`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace` status `INCOMPLETE_RELEASE` skills `0` hash `705fb20887dcbd4a2e25816a547d25ca589a9c49b3f641020b0ec58d8cefd754`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/01-v05-baseline/ai-drama-skills-v0.5-final` status `INCOMPLETE_RELEASE` skills `0` hash `ca426676039167be74b2cc0e0ddea1f775030346f7f5aa642d2ae32456b9d14b`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `56f9304981d6ad3147acf29b56ae339b641f2255a72c4e8b426c266c03041d5c`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-4/patch-1-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `22ca316893ab56eb3a2403e3eb4911b704503031b55999cd830ae696b5a8d09d`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-4/patch-2-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `e20cea0b5da73fb84f6b8ba4d6fa8631d97a1ecb494f55cd95af4543a235f479`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-4/patch-3-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `06b757a634bcbe01b818409ede3d66da99333d534355cd1732d6ce9a4144de49`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/patch-1-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `6ffc7036f0ad15cf2549ebd50cb29c0b4489e6603b156b5ca4cf4fcbebde0ff6`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/patch-2-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `7f7e53d930437a8e95a9743ada023282f14309af1fe8082b653296ac15dee02f`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/patch-3-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `6da0147223306d50be4bd7dca481973d982f3d9349bda6ec8c40bfbb2b856145`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/patch-4-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `574513cc1f58e5c90c5cba38ba6707595ad5bf2d0d86e283b9f851b02031c183`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/patch-4-verification-package/changed-files/03-wave-deliverables/wave-5/verification-runtime-snapshot/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `574513cc1f58e5c90c5cba38ba6707595ad5bf2d0d86e283b9f851b02031c183`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/patch-4-verification-package/verification-runtime-snapshot/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `2557b48bf7f4e2e846c95bc5d0b9edf5b3ffbc319e00737c778ad84b648d6344`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/patch-5-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `7ceed54eec4343a676991bbb8eea3290496153c95afd067f25956c6a87c86c41`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/patch-5-verification-package/changed-files/03-wave-deliverables/wave-5/verification-runtime-snapshot/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `7ceed54eec4343a676991bbb8eea3290496153c95afd067f25956c6a87c86c41`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/patch-5-verification-package/verification-runtime-snapshot/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `f13c27d9e7e4a8be4fb2bb6561c8af31fb47c9a1030c21bc0eafbbb45521718b`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/verification-runtime-snapshot/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `f13c27d9e7e4a8be4fb2bb6561c8af31fb47c9a1030c21bc0eafbbb45521718b`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/temp/wave3-corrective-patch-2-before/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `a746c61f363d06bcfd8588faa40dc74ffd97a10ccb9e4ab5e97946b082852cba`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/temp/wave4-corrective-patch-1-before/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `36969fb9c86a503ba14b3f64b22c49d7d67c9032d8bbfd4bf1b29426745d79d0`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/temp/wave4-corrective-patch-2-before/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `b5360923858536b11df1da01d494df427acafa02de5b08c7e41fa79c737e167e`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/temp/wave4-corrective-patch-3-before/02-v06-source/ai-drama-skills-v0.6` status `INCOMPLETE_RELEASE` skills `0` hash `bd0b144fc67861e4d73191f10d2826b3fb584784be3230bccef9f9fecc6ac717`
- `v0.3` `/Users/zengzhiwen/Downloads/ai-drama-skills-v0.3` status `INCOMPLETE_RELEASE` skills `0` hash `b946b5337fe590c274dbead25e2d4671e9152614a9c0f9a7e965ad868273e0b1`
- `v0.3` `/Users/zengzhiwen/workspace/zengzhiwen/local-karparthy-knowledge/raw/imports/ai-drama-skills-v0.3` status `INCOMPLETE_RELEASE` skills `0` hash `b946b5337fe590c274dbead25e2d4671e9152614a9c0f9a7e965ad868273e0b1`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-3/ai-drama-skills-v0.6-wave-3-patch-2-verification-package.zip` status `COMPLETE_RELEASE_ARCHIVE_CANDIDATE` skills `3` hash `416b11773b6954e4978d4f4c6ac85174988840deed27cadb74fadcf6ad944487`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-4/ai-drama-skills-v0.6-wave-4-patch-1-verification-package.zip` status `COMPLETE_RELEASE_ARCHIVE_CANDIDATE` skills `2` hash `a913247da66890aa93592e10c1a8f89ebcfbbe8fbce0df14876db9488b8662a4`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-4/ai-drama-skills-v0.6-wave-4-patch-2-verification-package.zip` status `COMPLETE_RELEASE_ARCHIVE_CANDIDATE` skills `2` hash `7aba00f9e9b5679b4d6f122dc647a09578174b02de64a60688dee8c432fd52ad`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/ai-drama-skills-v0.6-wave-5-patch-1-verification-package.zip` status `COMPLETE_RELEASE_ARCHIVE_CANDIDATE` skills `1` hash `c842e0ded9db1ea90ba52565fb16c53f0d561642d20ad5a4cac789067729ed82`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/ai-drama-skills-v0.6-wave-5-patch-2-verification-package.zip` status `COMPLETE_RELEASE_ARCHIVE_CANDIDATE` skills `1` hash `e303f15aaf351473265456db3bffcf94613c746a75b74cf4e3232fd08444625f`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/ai-drama-skills-v0.6-wave-5-patch-4-verification-package.zip` status `COMPLETE_RELEASE_ARCHIVE_CANDIDATE` skills `1` hash `bce0e7ccd8eb9ec96e209674c011d72f7b18fa49eaa8d39d0c451b3074e515ec`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/03-wave-deliverables/wave-5/ai-drama-skills-v0.6-wave-5-patch-5-verification-package.zip` status `COMPLETE_RELEASE_ARCHIVE_CANDIDATE` skills `1` hash `9b2eb42fd6a9c79e697317a0a3eebce12431a8c4f528eff82cace5b1d275ed3d`
- `v0.6` `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/05-release/ai-drama-skills-v0.6.zip` status `COMPLETE_RELEASE_ARCHIVE_CANDIDATE` skills `13` hash `48d98aac7d84397c42cc7cae6504831851ab46e9d777f18f0a96e86221cc748a`

## Skill Package Inventory

| Skill | Version | Status | Source | Runtime | Web operation | Hash | Recommended action |
|---|---:|---|---|---:|---|---|---|
| ai-drama-character-bible-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-1/ai-drama-character-bible-skill` | no | `` | `f84ecf305af19faf04858b19acd0ad3fdd210bf25434864691ac574483a9f8da` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-image-prompt-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-2-verification-package/changed-files/batch-2/ai-drama-image-prompt-skill` | no | `` | `fabd55522e2ae3705a8edade510aed61ce8218407bd9537a7e715224c544ceca` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-image-prompt-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-2/ai-drama-image-prompt-skill` | no | `` | `c5a4fc85841487728759b65916dfd59f42261c7821883b64a5f2606db6c9fb0a` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-libtv-cli-execution-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-1-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6/batch-4/ai-drama-libtv-cli-execution-skill` | no | `` | `d086e4a1b85fcdaa2a0a7662024b4f5cacfb169cf31e1eef3ce50b4865b3507e` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-libtv-cli-execution-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-2-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6/batch-4/ai-drama-libtv-cli-execution-skill` | no | `` | `bd9470a8e93fa4bd17a37725017078c4dbc29335f6407971f14e5eb210407711` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-libtv-cli-execution-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-4-verification-package/verification-runtime-snapshot/02-v06-source/ai-drama-skills-v0.6/batch-4/ai-drama-libtv-cli-execution-skill` | no | `` | `1c46f56d334abef4b9d272686695b015afc250423b148480ed42224d6c618bb5` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-libtv-cli-execution-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-5-verification-package/verification-runtime-snapshot/02-v06-source/ai-drama-skills-v0.6/batch-4/ai-drama-libtv-cli-execution-skill` | no | `` | `51e64da52d14452e43c03c46632d1e892b96cc8a89a21ce16f5f1446fdf1de9f` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-libtv-cli-execution-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-4/ai-drama-libtv-cli-execution-skill` | no | `` | `41c36a8a3004ad84f9110ecadae15385eeffb43bec1bc9d3051ae680d527b175` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-libtv-cli-execution-skill | v0.5 | MISSING_FROM_RUNTIME | `ai-drama-libtv-cli-execution-skill` | no | `` | `a6a5096935de325c419e1b418a08409a94f01743f4d319caf9c5ab2ad3175abd` | Compare against canonical source before M7A integration. |
| ai-drama-project-setup-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-1/ai-drama-project-setup-skill` | no | `` | `9379f6ba99fba0ba36fe6a00808e7cecf1b177dfb3d97e3478f31c93bba2346d` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-prop-bible-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-1/ai-drama-prop-bible-skill` | no | `` | `71a9a560366b0be4e8ba7c256e5faaa75955563cb3a9341a75eeca21ddf13311` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-scene-bible-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-1/ai-drama-scene-bible-skill` | no | `` | `ce2a903a530641ce2a93ecd72d71f6f3f50ad219d364aea036d08dc459878dee` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-scene-stabilization-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-2-verification-package/changed-files/batch-2/ai-drama-scene-stabilization-skill` | no | `` | `e1d3295649dedbc9b8d2541f89c9b736e3c8d92d3808f7fa2f6c0ff6776dd621` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-scene-stabilization-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-2/ai-drama-scene-stabilization-skill` | no | `` | `735722c6071e44a9c264a210585d7e44a5cc1b1cef244879042c735c5ac5346c` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-scene-stabilization-skill | v0.5 | MISSING_FROM_RUNTIME | `ai-drama-scene-stabilization-skill` | no | `` | `7fbc4b3748579241c310fa9f5139a0040bd53d3406f11db9989ed370b5dd4973` | Compare against canonical source before M7A integration. |
| ai-drama-script-adaptation-skill | v0.6.1-rc2.4 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/docs-model-level-provider-tests-design/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4` | yes | `/api/chapters/{chapter_id}/script/generate` | `015ed042ad753766e92f8ea58cdf7742695a06462d7041148e4a7a0b4cb69fc4` | Use as current runtime baseline. |
| ai-drama-script-adaptation-skill | v0.6.1-rc2.4 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/docs-provider-model-management/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4` | yes | `/api/chapters/{chapter_id}/script/generate` | `015ed042ad753766e92f8ea58cdf7742695a06462d7041148e4a7a0b4cb69fc4` | Use as current runtime baseline. |
| ai-drama-script-adaptation-skill | v0.6.1-rc2.4 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-m6d-management-ui/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4` | yes | `/api/chapters/{chapter_id}/script/generate` | `015ed042ad753766e92f8ea58cdf7742695a06462d7041148e4a7a0b4cb69fc4` | Use as current runtime baseline. |
| ai-drama-script-adaptation-skill | v0.6.1-rc2.4 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-m6e-migration-acceptance/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4` | yes | `/api/chapters/{chapter_id}/script/generate` | `015ed042ad753766e92f8ea58cdf7742695a06462d7041148e4a7a0b4cb69fc4` | Use as current runtime baseline. |
| ai-drama-script-adaptation-skill | v0.6.1-rc2.4 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-model-level-provider-tests/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4` | yes | `/api/chapters/{chapter_id}/script/generate` | `015ed042ad753766e92f8ea58cdf7742695a06462d7041148e4a7a0b4cb69fc4` | Use as current runtime baseline. |
| ai-drama-script-adaptation-skill | v0.6.1-rc2.4 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/impl-phase3-shot-prompt-foundation/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4` | yes | `/api/chapters/{chapter_id}/script/generate` | `015ed042ad753766e92f8ea58cdf7742695a06462d7041148e4a7a0b4cb69fc4` | Use as current runtime baseline. |
| ai-drama-script-adaptation-skill | v0.6.1-rc2.4 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/impl-phase3a-store-migration/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4` | yes | `/api/chapters/{chapter_id}/script/generate` | `015ed042ad753766e92f8ea58cdf7742695a06462d7041148e4a7a0b4cb69fc4` | Use as current runtime baseline. |
| ai-drama-script-adaptation-skill | v0.6.1-rc2.4 | CURRENT | `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4` | yes | `/api/chapters/{chapter_id}/script/generate` | `015ed042ad753766e92f8ea58cdf7742695a06462d7041148e4a7a0b4cb69fc4` | Use as current runtime baseline. |
| ai-drama-script-adaptation-skill | v0.6 | MISSING_FROM_RUNTIME | `batch-1/ai-drama-script-adaptation-skill` | no | `` | `e49b285bbb3b3b5f2f2e3341459592e4e2d2b6ce949f76caf1f7f5156d03f3c7` | Compare against canonical source before M7A integration. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2 | v0.6.1-rc2 | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-adaptation-skill-v0.6.1-rc2` | no | `` | `d6bf0f598eea811f688c2b207d41836e3b7217b54625bb013658ead33b551757` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.1 | v0.6.1-rc2.1 | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-adaptation-skill-v0.6.1-rc2.1` | no | `` | `1278c65fbe1e05e6fb5111c39be67af95ee22657dcef823bbc200c7152343cfe` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.1-runtime | v061 | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-adaptation-skill-v0.6.1-rc2.1-runtime` | no | `` | `918989de588e8bf3ab48e2bf071e93600a22b84fc17111b8df18eee1c994b269` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.2 | v0.6.1-rc2.2 | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-adaptation-skill-v0.6.1-rc2.2` | no | `` | `9e72d7fc8ed3a7b80f125a28ce5b840efcda11eb6dd03b4a0f8d0c315eff0e40` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.2 | v0.6.1-rc2.2 | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-adaptation-skill-v0.6.1-rc2.2` | no | `` | `9e72d7fc8ed3a7b80f125a28ce5b840efcda11eb6dd03b4a0f8d0c315eff0e40` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.2-runtime | v0.6.1-rc2.2 | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-adaptation-skill-v0.6.1-rc2.2-runtime` | no | `` | `1a913acbae91c3796eaffa647f9f77f7ea67f453573b08431a327a5338b16c3c` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.3-phase-b |  | MISSING_FROM_RUNTIME | `ai-drama-script-agent-lab/04-work/ai-drama-script-adaptation-skill-v0.6.1-rc2.3-phase-b` | no | `` | `e99f2ab93c942d667ee12f86c4b8ac9c2f76a86362aee54ee4036052a9c4787b` | Compare against canonical source before M7A integration. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.3-phase-b | v0.6.1-rc2.3 | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-adaptation-skill-v0.6.1-rc2.3-phase-b` | no | `` | `e01946f2118924a7165b7eee259fe2ff34c253473d0bee18667d97856259ae0e` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r1 |  | MISSING_FROM_RUNTIME | `ai-drama-script-agent-lab/04-work/ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r1` | no | `` | `edaa81f1791faaea49a41861f9dffc8a6d338bc83a158adab21964e41a949635` | Compare against canonical source before M7A integration. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r1 | v0.6.1-rc2.3 | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r1` | no | `` | `d3dd1976e0c8959c605c6d5ec54ed94be0e9165a3f44b775f62bba628b9086be` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r2 |  | MISSING_FROM_RUNTIME | `ai-drama-script-agent-lab/04-work/ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r2` | no | `` | `6982ad28c483040a534f79e71abf38418ec2eb425534df6d2dfeca5d54b3497e` | Compare against canonical source before M7A integration. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r2 | v0.6.1-rc2.3 | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r2` | no | `` | `0de7a82b0fd76e2020992371fc4b97b2f8a2de2b11f1710b3d52271e0f8f8605` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r3 |  | MISSING_FROM_RUNTIME | `ai-drama-script-agent-lab/04-work/ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r3` | no | `` | `dd7f5370b5efea9093fee6aca3c20172e0f4ae598b1865b0b9ab87b8f49a4e25` | Compare against canonical source before M7A integration. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r3 | v0.6.1-rc2.3 | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-adaptation-skill-v0.6.1-rc2.3-r3` | no | `` | `0b35f8672196f2525c100c5849f8a45d72b993f3b846c916278830ecdaa06117` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-script-adaptation-skill-v0.6.1-rc2.4 |  | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-agent-lab/04-work/ai-drama-script-adaptation-skill-v0.6.1-rc2.4` | no | `` | `1514b82137b27369185a7dc2a0bad1ce4034fdebdd18b4e73d791dc4ea71385c` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-series-canon-extraction-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-1/ai-drama-series-canon-extraction-skill` | no | `` | `94387ab9000005156705c410bb0b75e0da06d1eaef729254ac6177717da55078` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-series-canon-extraction-skill | v0.5 | MISSING_FROM_RUNTIME | `ai-drama-series-canon-extraction-skill` | no | `` | `93641105ed1d52b4c959cc0db1157619f844d80c903f8293d27a87ae667775f7` | Compare against canonical source before M7A integration. |
| ai-drama-shot-prompt-skill | v0.1.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/docs-model-level-provider-tests-design/skills/ai-drama-shot-prompt-skill/v0.1.0` | yes | `/api/chapters/{chapter_id}/shot-prompts/generate` | `74fbb54d178576dff570ce8f9a3ed836868e62a8e9ab9a6da5428504561fff1e` | Use as current runtime baseline. |
| ai-drama-shot-prompt-skill | v0.1.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/docs-provider-model-management/skills/ai-drama-shot-prompt-skill/v0.1.0` | yes | `/api/chapters/{chapter_id}/shot-prompts/generate` | `74fbb54d178576dff570ce8f9a3ed836868e62a8e9ab9a6da5428504561fff1e` | Use as current runtime baseline. |
| ai-drama-shot-prompt-skill | v0.1.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-m6d-management-ui/skills/ai-drama-shot-prompt-skill/v0.1.0` | yes | `/api/chapters/{chapter_id}/shot-prompts/generate` | `74fbb54d178576dff570ce8f9a3ed836868e62a8e9ab9a6da5428504561fff1e` | Use as current runtime baseline. |
| ai-drama-shot-prompt-skill | v0.1.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-m6e-migration-acceptance/skills/ai-drama-shot-prompt-skill/v0.1.0` | yes | `/api/chapters/{chapter_id}/shot-prompts/generate` | `74fbb54d178576dff570ce8f9a3ed836868e62a8e9ab9a6da5428504561fff1e` | Use as current runtime baseline. |
| ai-drama-shot-prompt-skill | v0.1.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-model-level-provider-tests/skills/ai-drama-shot-prompt-skill/v0.1.0` | yes | `/api/chapters/{chapter_id}/shot-prompts/generate` | `74fbb54d178576dff570ce8f9a3ed836868e62a8e9ab9a6da5428504561fff1e` | Use as current runtime baseline. |
| ai-drama-shot-prompt-skill | v0.1.0 | CURRENT | `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime/skills/ai-drama-shot-prompt-skill/v0.1.0` | yes | `/api/chapters/{chapter_id}/shot-prompts/generate` | `74fbb54d178576dff570ce8f9a3ed836868e62a8e9ab9a6da5428504561fff1e` | Use as current runtime baseline. |
| ai-drama-shot-prompt-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-1-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6/batch-3/ai-drama-shot-prompt-skill` | no | `` | `9cd721f880c998593d338c5872573060bb755d716c1f0fea910dd3c69d5fb41b` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-shot-prompt-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-2-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6/batch-3/ai-drama-shot-prompt-skill` | no | `` | `e57eae3309165ea0a1bd20a2d642529d8f2f05c88f440cc4eb9959210e076a90` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-shot-prompt-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-3/ai-drama-shot-prompt-skill` | no | `` | `52d2ce09ba6a08af99145ab5d7e6102b938a0761a1f279631317ad3b8b98e720` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-storyboard-design-skill | v0.1.0 | OBSOLETE | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/docs-model-level-provider-tests-design/skills/ai-drama-storyboard-design-skill/v0.1.0` | yes | `` | `38199d0bdf073195a2312bdb9bc381cfb01744e2f814ebcac91b33a1d0fa387f` | Keep reference; candidate for archive after approval. |
| ai-drama-storyboard-design-skill | v0.2.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/docs-model-level-provider-tests-design/skills/ai-drama-storyboard-design-skill/v0.2.0` | yes | `` | `c6173c1c6e556072df6839a6cce65f4b8788090728c0745e2f24c774c917c145` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.2.1 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/docs-model-level-provider-tests-design/skills/ai-drama-storyboard-design-skill/v0.2.1` | yes | `/api/chapters/{chapter_id}/storyboard/generate` | `156b2221876e9b8d22ea0147cf2984b2c79bc3067b866de226aa503bffb2ce6d` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.1.0 | OBSOLETE | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/docs-provider-model-management/skills/ai-drama-storyboard-design-skill/v0.1.0` | yes | `` | `38199d0bdf073195a2312bdb9bc381cfb01744e2f814ebcac91b33a1d0fa387f` | Keep reference; candidate for archive after approval. |
| ai-drama-storyboard-design-skill | v0.2.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/docs-provider-model-management/skills/ai-drama-storyboard-design-skill/v0.2.0` | yes | `` | `c6173c1c6e556072df6839a6cce65f4b8788090728c0745e2f24c774c917c145` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.2.1 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/docs-provider-model-management/skills/ai-drama-storyboard-design-skill/v0.2.1` | yes | `/api/chapters/{chapter_id}/storyboard/generate` | `156b2221876e9b8d22ea0147cf2984b2c79bc3067b866de226aa503bffb2ce6d` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.1.0 | OBSOLETE | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-m6d-management-ui/skills/ai-drama-storyboard-design-skill/v0.1.0` | yes | `` | `38199d0bdf073195a2312bdb9bc381cfb01744e2f814ebcac91b33a1d0fa387f` | Keep reference; candidate for archive after approval. |
| ai-drama-storyboard-design-skill | v0.2.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-m6d-management-ui/skills/ai-drama-storyboard-design-skill/v0.2.0` | yes | `` | `c6173c1c6e556072df6839a6cce65f4b8788090728c0745e2f24c774c917c145` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.2.1 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-m6d-management-ui/skills/ai-drama-storyboard-design-skill/v0.2.1` | yes | `/api/chapters/{chapter_id}/storyboard/generate` | `156b2221876e9b8d22ea0147cf2984b2c79bc3067b866de226aa503bffb2ce6d` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.1.0 | OBSOLETE | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-m6e-migration-acceptance/skills/ai-drama-storyboard-design-skill/v0.1.0` | yes | `` | `38199d0bdf073195a2312bdb9bc381cfb01744e2f814ebcac91b33a1d0fa387f` | Keep reference; candidate for archive after approval. |
| ai-drama-storyboard-design-skill | v0.2.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-m6e-migration-acceptance/skills/ai-drama-storyboard-design-skill/v0.2.0` | yes | `` | `c6173c1c6e556072df6839a6cce65f4b8788090728c0745e2f24c774c917c145` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.2.1 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-m6e-migration-acceptance/skills/ai-drama-storyboard-design-skill/v0.2.1` | yes | `/api/chapters/{chapter_id}/storyboard/generate` | `156b2221876e9b8d22ea0147cf2984b2c79bc3067b866de226aa503bffb2ce6d` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.1.0 | OBSOLETE | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-model-level-provider-tests/skills/ai-drama-storyboard-design-skill/v0.1.0` | yes | `` | `38199d0bdf073195a2312bdb9bc381cfb01744e2f814ebcac91b33a1d0fa387f` | Keep reference; candidate for archive after approval. |
| ai-drama-storyboard-design-skill | v0.2.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-model-level-provider-tests/skills/ai-drama-storyboard-design-skill/v0.2.0` | yes | `` | `c6173c1c6e556072df6839a6cce65f4b8788090728c0745e2f24c774c917c145` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.2.1 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/feat-model-level-provider-tests/skills/ai-drama-storyboard-design-skill/v0.2.1` | yes | `/api/chapters/{chapter_id}/storyboard/generate` | `156b2221876e9b8d22ea0147cf2984b2c79bc3067b866de226aa503bffb2ce6d` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.1.0 | OBSOLETE | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/impl-phase3-shot-prompt-foundation/skills/ai-drama-storyboard-design-skill/v0.1.0` | yes | `` | `38199d0bdf073195a2312bdb9bc381cfb01744e2f814ebcac91b33a1d0fa387f` | Keep reference; candidate for archive after approval. |
| ai-drama-storyboard-design-skill | v0.2.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/impl-phase3-shot-prompt-foundation/skills/ai-drama-storyboard-design-skill/v0.2.0` | yes | `` | `c6173c1c6e556072df6839a6cce65f4b8788090728c0745e2f24c774c917c145` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.2.1 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/impl-phase3-shot-prompt-foundation/skills/ai-drama-storyboard-design-skill/v0.2.1` | yes | `/api/chapters/{chapter_id}/storyboard/generate` | `156b2221876e9b8d22ea0147cf2984b2c79bc3067b866de226aa503bffb2ce6d` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.1.0 | OBSOLETE | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/impl-phase3a-store-migration/skills/ai-drama-storyboard-design-skill/v0.1.0` | yes | `` | `38199d0bdf073195a2312bdb9bc381cfb01744e2f814ebcac91b33a1d0fa387f` | Keep reference; candidate for archive after approval. |
| ai-drama-storyboard-design-skill | v0.2.0 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/impl-phase3a-store-migration/skills/ai-drama-storyboard-design-skill/v0.2.0` | yes | `` | `c6173c1c6e556072df6839a6cce65f4b8788090728c0745e2f24c774c917c145` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.2.1 | CURRENT | `/Users/zengzhiwen/.config/superpowers/worktrees/ai-drama-skill-runtime/impl-phase3a-store-migration/skills/ai-drama-storyboard-design-skill/v0.2.1` | yes | `/api/chapters/{chapter_id}/storyboard/generate` | `156b2221876e9b8d22ea0147cf2984b2c79bc3067b866de226aa503bffb2ce6d` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.1.0 | OBSOLETE | `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.1.0` | yes | `` | `38199d0bdf073195a2312bdb9bc381cfb01744e2f814ebcac91b33a1d0fa387f` | Keep reference; candidate for archive after approval. |
| ai-drama-storyboard-design-skill | v0.2.0 | CURRENT | `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.2.0` | yes | `` | `c6173c1c6e556072df6839a6cce65f4b8788090728c0745e2f24c774c917c145` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.2.1 | CURRENT | `/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.2.1` | yes | `/api/chapters/{chapter_id}/storyboard/generate` | `156b2221876e9b8d22ea0147cf2984b2c79bc3067b866de226aa503bffb2ce6d` | Use as current runtime baseline. |
| ai-drama-storyboard-design-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-1-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6/batch-3/ai-drama-storyboard-design-skill` | no | `` | `b672ac50a363428d618929ffe9dc1539a66a0c1bd035f7499ce04ae4bfff7174` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-storyboard-design-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-2-verification-package/changed-files/02-v06-source/ai-drama-skills-v0.6/batch-3/ai-drama-storyboard-design-skill` | no | `` | `e093859de98bd669a8ab1926cbb16f8f846e92eec426939addac99a5bb9802f2` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-storyboard-design-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-3/ai-drama-storyboard-design-skill` | no | `` | `fdee50dce599429ec9947c0754f858577ef05f4b32422cf727d0b04054d98039` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-visual-anchor-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `patch-2-verification-package/changed-files/batch-2/ai-drama-visual-anchor-skill` | no | `` | `c3359fdb8db7effefbe60fc85f82b6f17abb2b373bbd6e55acc6adb3d09369ea` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-visual-anchor-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-2/ai-drama-visual-anchor-skill` | no | `` | `ab4f8162f6fdcb1bb92e9876d663e684bdded4b4b78a069812730eb60a89ae2c` | Evaluate for M7A migration; do not auto-switch. |
| ai-drama-workflow-orchestrator-skill | v0.6 | NEWER_LOCAL_NOT_IN_RUNTIME | `batch-0/ai-drama-workflow-orchestrator-skill` | no | `` | `caca50c75d3400a72a6ba350cd47ce47c7a1b10e1ddc2ce0cfcf706dd0ff23d1` | Evaluate for M7A migration; do not auto-switch. |
| runtime |  | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-agent-lab/05-live-reproduction/second-live-reproduction-r3/runtime` | no | `` | `b741eced69be3dfd60682f9d5594e9d3faa1a595be4b9a4dfc1474069134709f` | Evaluate for M7A migration; do not auto-switch. |
| runtime |  | NEWER_LOCAL_NOT_IN_RUNTIME | `ai-drama-script-agent-lab/05-live-reproduction/v0.6.1-rc2.4-isolated-reproduction/runtime` | no | `` | `b13d853d68e89854e018494bae92a5bcfed4404a6882a557d7b2758f5be3e656` | Evaluate for M7A migration; do not auto-switch. |
| v05-script-skill |  | NEWER_LOCAL_NOT_IN_RUNTIME | `evidence/skill-sources/v05-script-skill` | no | `` | `ff80f8c50f147741a2d60e8af669a8735410ec1e1e34037e80b9044696fe812b` | Evaluate for M7A migration; do not auto-switch. |
| v06-orchestrator |  | NEWER_LOCAL_NOT_IN_RUNTIME | `evidence/skill-sources/v06-orchestrator` | no | `` | `0bc3ee8ff8f6b1ff66d23f3c8e6b4ebd0313fa7db6773e900505b791fca8fb44` | Evaluate for M7A migration; do not auto-switch. |
| v06-script-skill |  | NEWER_LOCAL_NOT_IN_RUNTIME | `evidence/skill-sources/v06-script-skill` | no | `` | `4c877707146da6df0bf04a095a42d7951fb3c66b38f054ee18dd22264e8f01cb` | Evaluate for M7A migration; do not auto-switch. |

## File Classification Summary

- `KEEP_REFERENCE`: `95721`
- `ARCHIVE_CANDIDATE`: `10`
- `KEEP_CANONICAL`: `30`
- `OBSOLETE`: `8`
- `DUPLICATE_EXACT`: `56338`
- `DUPLICATE_DIVERGED`: `6073`

## Archive And Duplicate Evidence

- Exact duplicate count: `56338`
- Diverged duplicate count: `6073`
- Archive candidate count: `10`

## M7A Baselines

- `M7A_SOURCE_BASELINE`: `/Users/zengzhiwen/AI-manju/ai-drama-skills-v0.6-workspace/05-release/ai-drama-skills-v0.6.zip`
- `M7A_RUNTIME_BASELINE`: `ai-drama-script-adaptation-skill@v0.6.1-rc2.4, ai-drama-shot-prompt-skill@v0.1.0, ai-drama-storyboard-design-skill@v0.2.1`
- `M7A_MISSING_SKILLS`: `ai-drama-character-bible-skill, ai-drama-image-prompt-skill, ai-drama-libtv-cli-execution-skill, ai-drama-project-setup-skill, ai-drama-prop-bible-skill, ai-drama-scene-bible-skill, ai-drama-scene-stabilization-skill, ai-drama-series-canon-extraction-skill, ai-drama-visual-anchor-skill, ai-drama-workflow-orchestrator-skill`
- `M7A_ORCHESTRATOR_STATUS`: `NEWER_LOCAL_NOT_IN_RUNTIME`

## Suggested Integration Order

1. shared contracts / schemas: requires source confirmation
1. workflow orchestrator: requires source confirmation
1. material extraction: requires source confirmation
1. ai-drama-script-adaptation-skill: present
1. ai-drama-character-bible-skill: present
1. ai-drama-scene-bible-skill: present
1. ai-drama-prop-bible-skill: present
1. ai-drama-visual-anchor-skill: present
1. ai-drama-storyboard-design-skill: present
1. ai-drama-image-prompt-skill: present
1. ai-drama-shot-prompt-skill: present
1. video execution: requires source confirmation
1. video QC: requires source confirmation

## Safety Notes

- No original files were deleted, moved, renamed, overwritten, or extracted into their original directories.
- No real Provider request was made.
- Runtime database business rows, credentials, signed URLs, image/video body content, and Provider output bodies were not read or reported.
- Archives were inspected through Python zip/tar listing APIs and manifest reads only.
