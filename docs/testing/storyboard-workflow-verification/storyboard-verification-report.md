# Storyboard Verification Report

## 1. Environment
- tested branch: test/storyboard-complete-verification
- tested commit sha: 103fd14ccdf5587142c7800f2c48c719a5bb4d38
- tested worktree clean: True
- Python: 3.9.6
- OS: Darwin
- working tree: clean
- CLI entry: python3 tools/verify_storyboard_workflow.py

## 2. Static Verification
{
  "migration_verify": {
    "command": "/Library/Developer/CommandLineTools/usr/bin/python3 migration/tools/verify_migration.py",
    "returncode": 0,
    "stdout": "{\n  \"status\": \"valid\",\n  \"checked_files\": 81\n}\n",
    "stderr": ""
  },
  "py_compile": {
    "command": "/Library/Developer/CommandLineTools/usr/bin/python3 -m py_compile /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/migration/tools/verify_migration.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/tools/verify_storyboard_workflow.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/__init__.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/acceptance.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/cli.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/manifest.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/parser.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/registry.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/request.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/runtime.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/script_validator.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/services.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/store.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/ai_drama_runtime/validators.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/common.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_artifact_integrity.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_assumptions_and_extensions.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_core_story_beats.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_coverage_evidence.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_creator_presentation.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_genericity.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_handoff_contract.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_markdown_json_equivalence.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_schema.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_source_claim_audit.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/runtime-validators/script_revision_structure.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.1.0/validators/common.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_genericity.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_continuity.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_duration.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_source_coverage.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_structure.py /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime/tests/acceptance/test_storyboard_workflow_acceptance.py",
    "returncode": 0,
    "stdout": "",
    "stderr": ""
  },
  "direct_pytest": {
    "command": "/Library/Developer/CommandLineTools/usr/bin/python3 -m pytest -q",
    "returncode": 0,
    "stdout": "........................................................................ [ 78%]\n....................                                                     [100%]\n92 passed in 25.18s\n",
    "stderr": "",
    "passed": 92,
    "skipped": 0,
    "skip_reason": "not skipped"
  },
  "verifier_inner_pytest": {
    "command": "/Library/Developer/CommandLineTools/usr/bin/python3 -m pytest -q",
    "returncode": 0,
    "stdout": "..s..................................................................... [ 78%]\n....................                                                     [100%]\n=========================== short test summary info ============================\nSKIPPED [1] tests/acceptance/test_storyboard_workflow_acceptance.py:23: skip recursive self-test inside verification entrypoint\n91 passed, 1 skipped in 12.36s\n",
    "stderr": "",
    "passed": 91,
    "skipped": 1,
    "skip_reason": "recursive self-test guard"
  }
}

## 3. Skill Package
{
  "script": {
    "skill_ref": "ai-drama-script-adaptation-skill@v0.6.1-rc2.4",
    "version": "v0.6.1-rc2.4",
    "content_hash": "b38eae160957484c68b7d47973a8b45419266d33c83b35de91be7291679d845f"
  },
  "storyboard": {
    "skill_ref": "ai-drama-storyboard-design-skill@v0.1.0",
    "version": "v0.1.0",
    "execution_profile": "storyboard-markdown-mvp-v1",
    "input_types": [
      "approved_script_revision"
    ],
    "output_types": [
      "storyboard_revision"
    ],
    "required_validators": [
      "storyboard_structure",
      "storyboard_duration",
      "storyboard_source_coverage",
      "storyboard_continuity"
    ],
    "package_hash": "347b27cfeb0b08c7d1acf825daacd6723f194d933ed34c0bdd18d821f3478230",
    "support_files": [
      "validators/common.py"
    ],
    "context_files": [
      "README.md",
      "CHANGELOG.md",
      "MIGRATION-NOTES.md",
      "requirements.txt",
      "references/storyboard-rules.md",
      "references/source-staleness-policy.md",
      "references/shot-boundary-policy.md",
      "references/continuity-policy.md",
      "templates/storyboard-outline.template.md",
      "templates/storyboard-outline.template.json",
      "schemas/storyboard-outline.schema.json",
      "schemas/storyboard-coverage.schema.json",
      "contracts/storyboard-design-contract-v1.md",
      "contracts/storyboard-approval-contract-v1.md",
      "runtime-validators/forbidden-terms.txt"
    ]
  }
}

## 4. Workflow Gates
{
  "script_run": {
    "run_id": "b360d68e225c4e6da68f491d5d044024",
    "revision_id": "c37329ee465c464b99bc5a57b690983f",
    "artifact_id": "shengsi-chapter-001",
    "approval_record": {
      "sequence": 1,
      "record_id": "191fd857c39147108ace296578e3bc7b",
      "revision_id": "c37329ee465c464b99bc5a57b690983f",
      "artifact_id": "shengsi-chapter-001",
      "action": "script_approved",
      "reviewer": "verifier",
      "note": "",
      "created_at": "2026-06-28T12:48:03.895524Z"
    },
    "content_hash": "ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a"
  },
  "script_approval": {
    "sequence": 1,
    "record_id": "191fd857c39147108ace296578e3bc7b",
    "revision_id": "c37329ee465c464b99bc5a57b690983f",
    "artifact_id": "shengsi-chapter-001",
    "action": "script_approved",
    "reviewer": "verifier",
    "note": "",
    "created_at": "2026-06-28T12:48:03.895524Z"
  },
  "storyboard_run": {
    "run_id": "4f9fd9dca391441a8d8f812dcd3bef52",
    "revision_id": "ef108da52ae9408dbd58ebbb7b9f67b8",
    "artifact_id": "shengsi-chapter-001:storyboard",
    "status": "SUCCEEDED",
    "freshness": "FRESH",
    "source_revision_id": "c37329ee465c464b99bc5a57b690983f",
    "source_approval_record": {
      "sequence": 1,
      "record_id": "191fd857c39147108ace296578e3bc7b",
      "revision_id": "c37329ee465c464b99bc5a57b690983f",
      "artifact_id": "shengsi-chapter-001",
      "action": "script_approved",
      "reviewer": "verifier",
      "note": "",
      "created_at": "2026-06-28T12:48:03.895524Z"
    },
    "content_hash": "e08a5f1a084858662578029458b2b036217c814b678be264f57340a29a6b78f8",
    "validator_results": [
      {
        "validator_id": "storyboard_structure",
        "status": "PASS",
        "required": true,
        "exit_code": 0,
        "error_code": "",
        "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"storyboard structure valid\", \"scenes\": 2}\n",
        "stderr": "",
        "report": {
          "final_status": "pass",
          "error_code": "",
          "message": "storyboard structure valid",
          "scenes": 2
        }
      },
      {
        "validator_id": "storyboard_duration",
        "status": "PASS",
        "required": true,
        "exit_code": 0,
        "error_code": "",
        "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"duration valid\", \"durations\": [6, 7, 8, 6], \"shot_count\": 4}\n",
        "stderr": "",
        "report": {
          "final_status": "pass",
          "error_code": "",
          "message": "duration valid",
          "durations": [
            6,
            7,
            8,
            6
          ],
          "shot_count": 4
        }
      },
      {
        "validator_id": "storyboard_source_coverage",
        "status": "PASS",
        "required": true,
        "exit_code": 0,
        "error_code": "",
        "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"source coverage valid\", \"source_scene_references\": [\"1-1\", \"1-1\", \"1-2\", \"1-2\"], \"missing_scene_references\": [], \"extra_scene_references\": []}\n",
        "stderr": "",
        "report": {
          "final_status": "pass",
          "error_code": "",
          "message": "source coverage valid",
          "source_scene_references": [
            "1-1",
            "1-1",
            "1-2",
            "1-2"
          ],
          "missing_scene_references": [],
          "extra_scene_references": []
        }
      },
      {
        "validator_id": "storyboard_continuity",
        "status": "PASS",
        "required": true,
        "exit_code": 0,
        "error_code": "",
        "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"continuity valid\", \"shot_count\": 4}\n",
        "stderr": "",
        "report": {
          "final_status": "pass",
          "error_code": "",
          "message": "continuity valid",
          "shot_count": 4
        }
      },
      {
        "validator_id": "genericity",
        "status": "NOT_APPLICABLE",
        "required": false,
        "exit_code": 0,
        "error_code": "",
        "stdout": "",
        "stderr": "validator applies to skill_package, not current revision type storyboard_revision\n",
        "report": {}
      }
    ]
  },
  "storyboard_revision": {
    "revision_id": "ef108da52ae9408dbd58ebbb7b9f67b8",
    "artifact_id": "shengsi-chapter-001:storyboard",
    "status": "SUCCEEDED",
    "content_hash": "e08a5f1a084858662578029458b2b036217c814b678be264f57340a29a6b78f8"
  },
  "validators": [
    {
      "validator_id": "storyboard_structure",
      "status": "PASS",
      "required": true,
      "exit_code": 0,
      "error_code": "",
      "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"storyboard structure valid\", \"scenes\": 2}\n",
      "stderr": "",
      "report": {
        "final_status": "pass",
        "error_code": "",
        "message": "storyboard structure valid",
        "scenes": 2
      }
    },
    {
      "validator_id": "storyboard_duration",
      "status": "PASS",
      "required": true,
      "exit_code": 0,
      "error_code": "",
      "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"duration valid\", \"durations\": [6, 7, 8, 6], \"shot_count\": 4}\n",
      "stderr": "",
      "report": {
        "final_status": "pass",
        "error_code": "",
        "message": "duration valid",
        "durations": [
          6,
          7,
          8,
          6
        ],
        "shot_count": 4
      }
    },
    {
      "validator_id": "storyboard_source_coverage",
      "status": "PASS",
      "required": true,
      "exit_code": 0,
      "error_code": "",
      "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"source coverage valid\", \"source_scene_references\": [\"1-1\", \"1-1\", \"1-2\", \"1-2\"], \"missing_scene_references\": [], \"extra_scene_references\": []}\n",
      "stderr": "",
      "report": {
        "final_status": "pass",
        "error_code": "",
        "message": "source coverage valid",
        "source_scene_references": [
          "1-1",
          "1-1",
          "1-2",
          "1-2"
        ],
        "missing_scene_references": [],
        "extra_scene_references": []
      }
    },
    {
      "validator_id": "storyboard_continuity",
      "status": "PASS",
      "required": true,
      "exit_code": 0,
      "error_code": "",
      "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"continuity valid\", \"shot_count\": 4}\n",
      "stderr": "",
      "report": {
        "final_status": "pass",
        "error_code": "",
        "message": "continuity valid",
        "shot_count": 4
      }
    },
    {
      "validator_id": "genericity",
      "status": "NOT_APPLICABLE",
      "required": false,
      "exit_code": 0,
      "error_code": "",
      "stdout": "",
      "stderr": "validator applies to skill_package, not current revision type storyboard_revision\n",
      "report": {}
    }
  ]
}

## 5. Runtime Flow
{
  "script_status": "SUCCEEDED",
  "storyboard_status": "SUCCEEDED",
  "storyboard_revision_id": "ef108da52ae9408dbd58ebbb7b9f67b8",
  "storyboard_artifact_id": "shengsi-chapter-001:storyboard",
  "source_revision_id": "c37329ee465c464b99bc5a57b690983f",
  "source_content_hash": "ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a",
  "source_approval_record_id": "191fd857c39147108ace296578e3bc7b",
  "request_hash": "15d79809361de71915f394f0a4cb0b8d7a488de52a05043eebe4d7143e740b11",
  "request_snapshot": {
    "context_files": [
      {
        "content": "# AI Drama Storyboard Design Skill\n\nFormal storyboard design package for approved drama script revisions.\n",
        "logical_type": "context",
        "relative_path": "README.md",
        "sha256": "44690a2d7fc41955720c48da7b6f2dc8de7d006e58d8defbf6fc7e06fa820cc7"
      },
      {
        "content": "# Changelog\n\n## v0.1.0\n\n- Initial formal storyboard skill package.\n",
        "logical_type": "context",
        "relative_path": "CHANGELOG.md",
        "sha256": "c2b46e2c1f025cb305329d43fdc8ce33dca2a66ea7c4a8e78eb6e465e28478fc"
      },
      {
        "content": "# Migration Notes\n\nThis package is newly created from approved storyboard requirements.\nIt is not a migration of an existing formal Storyboard Skill.\n",
        "logical_type": "context",
        "relative_path": "MIGRATION-NOTES.md",
        "sha256": "77ccd75901e97c91ad276967a0749753a4a17a84a085ef78a7ecad31d6714ad4"
      },
      {
        "content": "PyYAML>=6.0\n",
        "logical_type": "context",
        "relative_path": "requirements.txt",
        "sha256": "71749243f84428fee225bfaa796dca5ef6c1e83a98f6d2a407df615b0390d6fb"
      },
      {
        "content": "# Storyboard Rules\n\nStoryboard revisions must preserve approved script scene order, shot continuity, and upstream binding.\n",
        "logical_type": "context",
        "relative_path": "references/storyboard-rules.md",
        "sha256": "11ad719d044211bcd298fa5cd35123988afd30f9ebd564cee6c4f950049cee43"
      },
      {
        "content": "# Source Staleness Policy\n\nA storyboard revision becomes stale when its source script revision is no longer the current approved revision for the source script artifact.\n",
        "logical_type": "context",
        "relative_path": "references/source-staleness-policy.md",
        "sha256": "bd735f285125608e74eb9d023b9ffc10ebbc49774a5430d0a243a55169133338"
      },
      {
        "content": "# Shot Boundary Policy\n\nSplit scenes into shots using stable, source-grounded boundaries.\n",
        "logical_type": "context",
        "relative_path": "references/shot-boundary-policy.md",
        "sha256": "cd746dd92e506bffb2e5254d8fdffed7287af362e3c828170c3ddd1e0474ff51"
      },
      {
        "content": "# Continuity Policy\n\nEach shot must record continuity_in and continuity_out values.\n",
        "logical_type": "context",
        "relative_path": "references/continuity-policy.md",
        "sha256": "d3996b21606e8eabe3ddeef8a6a36f41616916424b3740d5f2d600d37ba7b5d1"
      },
      {
        "content": "# Storyboard\n\n## 场次：{scene_id}\n\n### 镜头 {shot_order}\n\n- scene_id: {scene_id}\n- shot_id: {shot_id}\n- shot_order: {shot_order}\n- source_scene_reference: {source_scene_reference}\n- duration_seconds: {duration_seconds}\n- shot_size: {shot_size}\n- camera_angle: {camera_angle}\n- camera_movement: {camera_movement}\n- visual_composition: {visual_composition}\n- character_positions: {character_positions}\n- character_actions: {character_actions}\n- emotion_performance: {emotion_performance}\n- dialogue: {dialogue}\n- sound_notes: {sound_notes}\n- continuity_in: {continuity_in}\n- continuity_out: {continuity_out}\n",
        "logical_type": "context",
        "relative_path": "templates/storyboard-outline.template.md",
        "sha256": "38bda79d09c72a227d78757c9645a060986fd6c085fea79abbf5369ac38df22c"
      },
      {
        "content": "{\n  \"scene_id\": \"{scene_id}\",\n  \"shots\": [\n    {\n      \"scene_id\": \"{scene_id}\",\n      \"shot_id\": \"{shot_id}\",\n      \"shot_order\": \"{shot_order}\",\n      \"source_scene_reference\": \"{source_scene_reference}\",\n      \"duration_seconds\": \"{duration_seconds}\",\n      \"shot_size\": \"{shot_size}\",\n      \"camera_angle\": \"{camera_angle}\",\n      \"camera_movement\": \"{camera_movement}\",\n      \"visual_composition\": \"{visual_composition}\",\n      \"character_positions\": \"{character_positions}\",\n      \"character_actions\": \"{character_actions}\",\n      \"emotion_performance\": \"{emotion_performance}\",\n      \"dialogue\": \"{dialogue}\",\n      \"sound_notes\": \"{sound_notes}\",\n      \"continuity_in\": \"{continuity_in}\",\n      \"continuity_out\": \"{continuity_out}\"\n    }\n  ]\n}\n",
        "logical_type": "context",
        "relative_path": "templates/storyboard-outline.template.json",
        "sha256": "b9d519cd06e68382550ed862e8f8f5ab32dc9d45cbccf3d208899fb5c4efafb9"
      },
      {
        "content": "{\n  \"$schema\": \"https://json-schema.org/draft/2020-12/schema\",\n  \"type\": \"object\",\n  \"required\": [\"scene_id\", \"shots\"],\n  \"additionalProperties\": false,\n  \"properties\": {\n    \"scene_id\": {\n      \"type\": \"string\",\n      \"minLength\": 1\n    },\n    \"shots\": {\n      \"type\": \"array\",\n      \"minItems\": 1,\n      \"items\": {\n        \"type\": \"object\",\n        \"required\": [\n          \"scene_id\",\n          \"shot_id\",\n          \"shot_order\",\n          \"source_scene_reference\",\n          \"duration_seconds\",\n          \"shot_size\",\n          \"camera_angle\",\n          \"camera_movement\",\n          \"visual_composition\",\n          \"character_positions\",\n          \"character_actions\",\n          \"emotion_performance\",\n          \"dialogue\",\n          \"sound_notes\",\n          \"continuity_in\",\n          \"continuity_out\"\n        ],\n        \"additionalProperties\": false,\n        \"properties\": {\n          \"scene_id\": {\"type\": \"string\", \"minLength\": 1},\n          \"shot_id\": {\"type\": \"string\", \"minLength\": 1},\n          \"shot_order\": {\"type\": \"integer\", \"minimum\": 1},\n          \"source_scene_reference\": {\"type\": \"string\", \"minLength\": 1},\n          \"duration_seconds\": {\"type\": \"integer\", \"minimum\": 5, \"maximum\": 15},\n          \"shot_size\": {\"type\": \"string\", \"minLength\": 1},\n          \"camera_angle\": {\"type\": \"string\", \"minLength\": 1},\n          \"camera_movement\": {\"type\": \"string\", \"minLength\": 1},\n          \"visual_composition\": {\"type\": \"string\", \"minLength\": 1},\n          \"character_positions\": {\"type\": \"string\", \"minLength\": 1},\n          \"character_actions\": {\"type\": \"string\", \"minLength\": 1},\n          \"emotion_performance\": {\"type\": \"string\", \"minLength\": 1},\n          \"dialogue\": {\"type\": \"string\", \"minLength\": 1},\n          \"sound_notes\": {\"type\": \"string\", \"minLength\": 1},\n          \"continuity_in\": {\"type\": \"string\", \"minLength\": 1},\n          \"continuity_out\": {\"type\": \"string\", \"minLength\": 1}\n        }\n      }\n    }\n  }\n}\n",
        "logical_type": "context",
        "relative_path": "schemas/storyboard-outline.schema.json",
        "sha256": "66bd14811036d2214979607f261da406b40efcbc77bd768c2f0263cc9ab04895"
      },
      {
        "content": "{\n  \"$schema\": \"https://json-schema.org/draft/2020-12/schema\",\n  \"type\": \"object\",\n  \"required\": [\"source_scene_references\", \"missing_scene_references\", \"extra_scene_references\"],\n  \"additionalProperties\": false,\n  \"properties\": {\n    \"source_scene_references\": {\n      \"type\": \"array\",\n      \"items\": {\"type\": \"string\", \"minLength\": 1},\n      \"minItems\": 1,\n      \"uniqueItems\": true\n    },\n    \"missing_scene_references\": {\n      \"type\": \"array\",\n      \"items\": {\"type\": \"string\", \"minLength\": 1},\n      \"uniqueItems\": true\n    },\n    \"extra_scene_references\": {\n      \"type\": \"array\",\n      \"items\": {\"type\": \"string\", \"minLength\": 1},\n      \"uniqueItems\": true\n    }\n  }\n}\n",
        "logical_type": "context",
        "relative_path": "schemas/storyboard-coverage.schema.json",
        "sha256": "6814495e8fd2da8c07670aa09ef6b9d68c59000087ccf0116a676c6757e299a8"
      },
      {
        "content": "# Storyboard Design Contract v1\n\n## Structure\n\n- Markdown only\n- `# Storyboard` title\n- `## 场次：{scene_id}` per scene\n- `### 镜头 {shot_order}` per shot\n\n## Required shot fields\n\nEach shot must define:\n\n- `scene_id`\n- `shot_id`\n- `shot_order`\n- `source_scene_reference`\n- `duration_seconds`\n- `shot_size`\n- `camera_angle`\n- `camera_movement`\n- `visual_composition`\n- `character_positions`\n- `character_actions`\n- `emotion_performance`\n- `dialogue`\n- `sound_notes`\n- `continuity_in`\n- `continuity_out`\n\n## Constraints\n\n- `duration_seconds` must be between 5 and 15.\n- `shot_id` must be unique across the chapter.\n- `shot_order` must be unique within a scene and increase monotonically.\n- `source_scene_reference` must cover every source scene without inventing new scenes.\n- No downstream execution terms, shot prompt packages, or platform parameters.\n\n## Source binding\n\nStoryboard revisions must cite the approved source script revision and its captured approval record in provenance.\n",
        "logical_type": "context",
        "relative_path": "contracts/storyboard-design-contract-v1.md",
        "sha256": "4b1c8ceec61fdc99c457fe137dfed4102201ebfad1fdc0b95bcbeb90383238a0"
      },
      {
        "content": "# Storyboard Approval Contract v1\n\nStoryboard approval is allowed only when:\n\n1. the storyboard revision is derived from the current approved script revision;\n2. all required storyboard validators ran and passed;\n3. no required validator was incorrectly marked not applicable;\n4. the source script approval record captured at generation time is preserved in provenance;\n5. the storyboard revision is fresh against the current approved script revision.\n\nApproval actions:\n\n- `storyboard_approved`\n- `storyboard_rejected`\n\nApproval must not rewrite source provenance after later script approvals.\n",
        "logical_type": "context",
        "relative_path": "contracts/storyboard-approval-contract-v1.md",
        "sha256": "dd11e4ef08b73b5bb4ac2cb129b2374c5fd4cae4b54f09b46914cb7ef400d970"
      },
      {
        "content": "FORBIDDEN_PROJECT_NAME\nFORBIDDEN_PROJECT_LINE\nFIXED_SAMPLE_BEAT_ID\n",
        "logical_type": "context",
        "relative_path": "runtime-validators/forbidden-terms.txt",
        "sha256": "0bd8c989300737eb12bb061db5c0ea271f5a89a20abc6b728ce1b3c273cdbafa"
      }
    ],
    "inputs": {
      "characters": "# 角色设定档案\n\n## 元数据\n- **作品**：商海沉浮·釜底抽薪篇\n- **宪法版本**：v2.0.0\n- **创建日期**：2026-06-16\n- **基于来源**：宪法、规格书、创作计划、30章实际内容\n\n---\n\n## 一、主角\n\n### 沈清荷（姐姐·商道之刃）\n\n#### 基本信息\n- **身份**：沈家长女，商业掌舵人\n- **年龄**：约二十岁（及笄之后，议亲阶段）\n- **父亲**：已故（生前是商人，教沈清荷经商）\n- **母亲**：未出场（人丁单薄的设定）\n\n#### 外貌特征\n- 手指常年握笔，指间有薄茧\n- 书房窗外的桂花树是她的精神锚点\n\n#### 性格层次\n\n**表层（对外）**：\n- 沉稳、话少、持重\n- 渣男眼中：\"温柔、好哄、听话的未婚妻\"\n\n**中层（对内）**：\n- 精于算计、冷静如棋手\n- 凡事用账本说话\n- 愤怒时不吼叫，在账本上记一笔\n\n**深层（核心）**：\n- 前世被利用至死，重生后的觉悟：爱情只是工具，财权才是根本\n- 对妹妹的愧疚与保护欲并存\n- 复仇不是情绪宣泄，是精心策划的商业战争\n\n#### 核心能力\n- 渠道掌控、资源调配\n- 对数字和账目过目不忘\n- 前世掌握盐铁渠道，这一世知道未来十年商业风向\n- 训练有素的商业直觉\n\n#### 标志性行为\n| 动作 | 触发时机 | 在文中的应用 |\n|------|---------|------------|\n| 拨动算盘珠 | 重大决定前 | 第1章、第6章、第20章、第30章 |\n| 在账本上记一笔 | 愤怒/记仇时 | 反复出现，贯穿全书 |\n| 给妹妹夹菜 | 开心时 | 姐妹互动场景 |\n| \"这笔账，划不来\" | 判断得失时 | 金句模式 |\n\n#### 前世经历\n- 被渣男利用商业才能，帮他平步青云登上户部高位\n- 被渣男挑拨离间，以为妹妹要毒杀自己\n- 临死前看到渣男搂着丞相之女林婉兮，亲口承认：\"我只是借你们沈家的钱袋子，铺我的青云路。\"\n- 被毒杀而死\n\n#### 今世成长弧线\n\n| 阶段 | 章节 | 状态 |\n|------|------|------|\n| 觉醒期 | 第1-3章 | 从震惊到清醒，与妹妹相认，确立复仇同盟 |\n| 布局期 | 第4-10章 | 截胡生意、记账、设陷阱，表面演痴情未婚妻 |\n| 发力期 | 第11-16章 | 改良制盐技术，开辟新渠道，蚕食渣男经济命脉 |\n| 收网期 | 第17-20章 | 引导渣男入局，伪造投资人，准备证据 |\n| 决裂期 | 第21-28章 | 送匿名信、当堂对质、撕婚书、烧婚约 |\n| 终局 | 第29-30章 | 拿下皇商资格，掌管三个盐铺，成为独立女商人 |\n\n#### 随身道具\n- **算盘**（核心道具）：第1章结尾第一次拨动 → 第30章最后放下\n- **账本**（秘密武器）：记录了渣男每一笔贪污、每一笔借款\n\n---\n\n### 沈清莲（妹妹·人心之网）\n\n#### 基本信息\n- **身份**：沈家次女，社交操盘手\n- **年龄**：约十七八岁\n- **训练经历**：十年\"察言观色、撒娇卖痴\"的训练（第2章自述）\n\n#### 外貌特征\n- 爱笑，笑容天真烂漫\n- 随身携带梅花团扇，绣线已有些松了（暗示使用频率之高）\n\n#### 性格层次\n\n**表层（对外）**：\n- 天真烂漫、笑语晏晏\n- 渣男眼中：\"崇拜自己的小姨子，好利用\"\n\n**中层（对内）**：\n- 通透机敏、话里藏刀\n- 最擅长用无辜的语气说出最致命的信息\n- 对姐姐真诚，对敌人演戏\n\n**深层（核心）**：\n- 前世痴迷渣男，被利用后惨死\n- 重生后最痛的不是被渣男害死，而是前世与姐姐反目\n- 她的复仇武器不是算盘，是人心\n\n#### 核心能力\n- 人际网络构建、情报收集\n- 十年社交训练：记住每个人的生辰、软肋和欲望\n- 前世广结善缘，掌握大量人脉情报\n- 借力打力——不需要亲自出手，让敌人自相残杀\n\n#### 标志性行为\n| 动作 | 触发时机 | 在文中的应用 |\n|------|---------|------------|\n| 团扇掩住嘴角笑意 | 说完致命信息后 | 第3章、第7章、第22章 |\n| 笑语晏晏，话里藏刀 | 社交场合 | 贯穿全书 |\n| \"哎呀，这可不巧了么\" | 算计得逞时 | 金句模式 |\n| 对姐姐真笑，对敌人假笑 | 角色切换时 | 社交场合与私下对比 |\n\n#### 前世经历\n- 被渣男甜言蜜语蒙蔽，前世与姐姐争风吃醋\n- 四处炫耀未婚夫深情，结果同样被利用至死\n- 重生方式：做了一场噩梦，梦中经历了前世的一切\n\n#### 今世成长弧线\n\n| 阶段 | 章节 | 状态 |\n|------|------|------|\n| 觉醒期 | 第1-3章 | 从噩梦中醒来，与姐姐对视即达成默契 |\n| 布局期 | 第4-10章 | 扮演崇拜渣男的小姨子，散播假消息 |\n| 发力期 | 第11-16章 | 社交策反，拉拢刘德旺，接触王夫人 |\n| 收网期 | 第17-20章 | 安排假投资人方老板，信息误导渣男 |\n| 决裂期 | 第21-28章 | 当面翻脸，公开揭露渣男真面目 |\n| 终局 | 第29-30章 | 创办清莲书院，三顾茅庐请方先生，完成独立 |\n\n#### 随身道具\n- **团扇**（核心道具）：梅花绣纹，绣线已松，每次说完致命信息掩嘴笑\n- **社交笔记**（暗线道具）：她能记住每个人的生辰、软肋和欲望\n\n---\n\n## 二、反派\n\n### 顾长渊（渣男世子）\n\n#### 基本信息\n- **身份**：侯府世子（爵位继承人）\n- **父亲**：老侯爷（仅侧面提及，第27章砸书房）\n- **母亲**：侯夫人（仅侧面提及，第27章清理院子）\n- **外表**：温润如玉，常穿月白色长衫\n- **年龄**：约二十出头\n\n#### 性格特征\n\n**表面**：\n- 温文尔雅，谦谦君子\n- 谈吐风雅，举止得体\n- 让人放下戒心的\"好人\"形象\n\n**内核**：\n- 极度自负，看不起商贾出身的沈家\n- 精于算计，商品是\"爱情\"\n- 核心信念：\"女人嘛，好哄\"、\"女人终究是女人\"\n- 贪婪且轻视女性——这是他致命的盲区\n\n#### 前世经历\n- 利用沈家姐妹的资源和感情，平步青云登上户部高位\n- 挑拨离间让两姐妹互斗至死\n- 最终搂着丞相之女林婉兮，亲口承认利用\n- \"我只是借你们沈家的钱袋子，铺我的青云路。\"\n\n#### 致命弱点\n- 自负：至死不信女人能有翻天的智慧\n- 贪婪：挪用公款、多线操作、越陷越深\n- 轻视女性：即使\"诸事不顺\"，也不怀疑姐妹\n- 真商人假君子：嘴上风雅，心里全是生意\n\n#### 罪行清单（实际内容统计）\n| 罪行 | 金额/内容 | 证据 |\n|------|---------|------|\n| 盐铺账目造假 | 近2000两 | 账本中\"特定\"\"杂项\"条目 |\n| 挪用户部公款 | 13000两 | 周书办被查获的私账 |\n| 向沈家多次借款 | 7000+两 | 借据（沈清荷保管） |\n| 虚假投资人协议 | 2000两 | 合伙契书（沈清荷保留） |\n| 抬高盐铺采购价中饱私囊 | 数额不明 | 赵四提供的证据 |\n\n#### 人物弧线（权力下坠曲线）\n\n| 章节 | 状态 | 关键事件 |\n|------|------|---------|\n| 第1-3章 | 志得意满 | 两个女人为我争风吃醋，一切尽在掌握 |\n| 第4-9章 | 隐隐不安 | 南货被截、传言四起，但归因于运气不好 |\n| 第10章 | 信心巅峰 | 拿下漕运资格，以为大计将成 |\n| 第13章 | 开始怀疑 | 派人调查，被姐妹完美伪装骗过 |\n| 第16-17章 | 焦虑加深 | 盐铺收入下降、粮商催款 |\n| 第18-19章 | 假装镇定 | 查账通过、投资到位，又放心了 |\n| 第20章 | 恍然大悟 | 三个关键人物同时消失，但不敢信是沈清荷 |\n| 第21-23章 | 疯狂补救 | 四处借钱被拒、周书办被抓、龙井茶出现在书房 |\n| 第24章 | 真相大白 | 姐妹当面对质，揭露一切 |\n| 第25章 | 彻底崩溃 | 公堂定罪、林婉兮冷眼、锒铛入狱 |\n| 第26-27章 | 无力挣扎 | 反咬失败、削爵、发配北疆 |\n| 第28章 | 彻底出局 | 婚约被撕毁、侯府试图挽回被拒 |\n\n#### 创作铁律\n- ✅ 聪明但自负——他不是蠢，是看不起女人\n- ✅ 在中期之前（第13-19章）察觉有\"幕后黑手\"但不信是姐妹\n- ✅ 不洗白——没有\"深情无奈\"的戏码\n- ✅ 结局：人财两空，身败名裂，发配边疆\n\n---\n\n## 三、核心盟友\n\n### 赵四（第一个内线）\n\n- **身份**：侯府盐铺二掌柜\n- **年龄**：约三十岁\n- **工龄**：为侯府工作六年\n- **性格**：老实本分、不善交际、孝顺\n- **家庭**：母亲常年咳疾，需要定期抓药；妹妹在绣坊做学徒\n- **住址**：侯府西边巷子第三家，门口有棵槐树\n- **被策反方式**：沈清莲亲自登门，承诺沈家铺子的职位、双倍月钱、让他照顾母亲\n- **作用**：\n  - 提供盐铺真实账目（揭露顾长渊抬高采购价中饱私囊）\n  - 向顾长渊提供假情报（雪盐日产量只有200斤，实际500斤）\n  - 成为姐妹在侯府内部的眼线\n- **出场**：第8章（策反）、第16章（提供假情报）\n\n### 陈伯远（制盐伙伴）\n\n- **身份**：盐匠，手艺人\n- **性格**：老实、技术好但不善经营\n- **地点**：原作坊在城外东边五六里，后迁至城东运河边\n- **技术**：只会做灰盐（低价）\n- **被提升方式**：沈清荷带着\"豆浆法\"找上门——卤水中加豆浆去除杂质，产出纯白如雪的\"雪盐\"\n- **合作关系**：沈清荷提供资金和销路，陈伯远提供技术，五五分账\n- **发展轨迹**：\n  - 第11章：小作坊，几口锅\n  - 第14章：六口大锅，日产500斤\n  - 第29章：八口锅→二十口锅，供应官盐\n- **出场**：第11章、第14章、第29章\n\n### 刘德旺（粮商盟友）\n\n- **身份**：京城粮商\n- **资历**：与侯府合作八年\n- **性格**：稳重、话少、守信、讲义气\n- **与渣男关系**：顾长渊欠他1800两粮款未还，早已不满\n- **被策反方式**：沈清莲在赏春宴上主动接触，暗示沈家更可靠\n- **策反条件**：沈家所有粮食业务过他的手，市价交易，不拖欠货款\n- **额外作用**：成为姐妹监控渣男动向的暗线\n- **出场**：第12章（初次接触）、第15章（正式入伙）\n\n### 方先生（书院教师）\n\n- **身份**：女性学者，曾在江南书院任教，退休回京\n- **出场**：第29章（沈清莲三顾茅庐，第三次带自酿桂花酒才请动）\n- **作用**：清莲书院第一位先生，象征沈清莲的事业独立\n\n---\n\n## 四、次要角色\n\n### 渣男阵营（被姐妹击败的一方）\n\n| 姓名 | 身份 | 与渣男关系 | 结局 |\n|------|------|----------|------|\n| 孙旺财 | 东市掮客 | 渣男找的中介 | 被沈清荷收买后消失（第20章） |\n| 周书办 | 户部书办，二十年老吏 | 渣男贪污同谋 | 匿名信举报后被逮捕（第23章） |\n| 吴管事 | 侯府管家 | 替渣男跑腿调查 | 调查无果 |\n| 钱管事 | 侯府账房，十年老仆 | 忠于侯府 | 给渣男最后500两私房钱（第21章） |\n| 王夫人 | 王御史之妻 | 社交圈信息来源 | 被沈清莲利用传播谣言 |\n| 张侍郎太太 | 吏部张侍郎之妻 | 社交圈信息来源 | 同上 |\n| 周三小姐 | 周家小姐 | 社交圈信息来源 | 同上 |\n| 吴老板 | 渣男远亲，西城丝绸商 | 曾受侯府两千两救命钱 | 拒绝借钱（第21章） |\n| 林老板 | 渣男前生意伙伴 | 曾被渣男帮过拿下河道工程 | 拒绝借钱：\"你拿什么还\"（第21章） |\n| 陈员外郎 | 户部官员 | 收过渣男礼 | 拒绝帮忙拖延调查（第22章） |\n\n### 中立/背景角色\n\n| 姓名 | 身份 | 作用 |\n|------|------|------|\n| 周老板 | 金陵周记商行 | 渣男想买他的南货，被沈清荷截胡（第4章） |\n| 马老板 | 漕运批文持有者 | 卖了一个批文（沈清荷通过中间人买下） |\n| 王掌柜 | 城南王家杂货铺 | 雪盐第一个零售点（第14章） |\n| 王主事 | 户部主事 | 渣男想贿赂的对象之一 |\n| 户部侍郎 | 户部二把手 | 收到匿名信、主持审判（第23、25章） |\n| 老侯爷 | 顾长渊之父 | 仅侧面提及，儿子事发后砸书房（第27章） |\n| 侯夫人 | 顾长渊之母 | 仅侧面提及，清理儿子院落（第27章） |\n| 刘管事 | 侯府管家，二十年老仆 | 替老侯爷送信试图挽回婚约（第28章） |\n| 李夫人 | 西城李府主人 | 第7章赏花宴主办者 |\n| 周侍郎 | 吏部官员 | 第2章被沈清莲提及有私生子 |\n\n---\n\n## 五、角色关系图谱\n\n```\n                    前世记忆（共同仇人）\n                         ↓\n    ┌──────────────────────────────────────┐\n    │                                      │\n┌───────┐  姐妹同盟（坚不可摧）  ┌───────┐\n│沈清荷  │ ←────────────────→  │沈清莲  │\n│商道之刃 │   算账 / 算人       │人心之网 │\n└───┬───┘                      └───┬───┘\n    │                              │\n    │ 截胡生意                     │ 策反拉拢\n    │ 改良制盐                     │ 散布谣言\n    │ 设陷阱                       │ 安插内线\n    │                              │\n    ▼                              ▼\n┌─────────────────────────────────────────┐\n│              顾长渊（渣男）              │\n│         侯府世子/月白长衫/温润如玉        │\n│           致命弱点：轻视女性              │\n│                                          │\n│  ←── 经济封锁（截胡/架空/造假）         │\n│  ←── 社交孤立（策反/谣言/内线）         │\n│  ←── 法律打击（匿名信/借据/账本证据）    │\n└─────────────────────────────────────────┘\n    │\n    │ 被击败后\n    ▼\n  削爵 + 发配北疆 + 终身不得回京\n```\n\n### 姐妹分工矩阵\n\n| 维度 | 沈清荷 | 沈清莲 |\n|------|--------|--------|\n| 核心武器 | 算盘（算账） | 团扇（算人） |\n| 战场 | 商场 | 社交场 |\n| 攻击方式 | 截胡/架空/垄断 | 策反/谣言/收买 |\n| 关键盟友 | 陈伯远、周老板 | 赵四、刘德旺、方先生 |\n| 金句 | \"这笔账，划不来\" | \"哎呀，这可不巧了么\" |\n| 终局成就 | 皇商掌权人 | 女子书院创办人 |\n\n### 情感纽带\n- **姐妹情**：通过动作细节表达——夹菜、对视、挡在身前、共饮酒\n- **对渣男**：零情感，纯工具，每一句甜言蜜语都是台词\n- **对盟友**：以利相交，同时给予尊重——不是施舍，是合作\n\n---\n\n## 六、角色一致性检查清单\n\n### 沈清荷\n- [x] 是否每次愤怒都在账本上记一笔而非吼叫？\n- [x] 是否重大决定前都拨动了算盘？\n- [x] 是否用数字和账本说话而非情绪？\n- [x] 是否对妹妹绝对信任？\n\n### 沈清莲\n- [x] 是否每次说到致命信息都用团扇掩笑？\n- [x] 是否对外人笑里藏刀，对姐姐笑里真诚？\n- [x] 是否发挥了\"记住每个人的软肋\"的能力？\n- [x] 是否对渣男零真情？\n\n### 顾长渊\n- [x] 是否始终轻视女性？\n- [x] 是否第20章前都没怀疑姐妹？\n- [x] 是否没被洗白？\n- [x] 是否结局符合\"人财两空、身败名裂\"？\n\n*创建时间：2026-06-16*\n*基于：宪法v2.0.0 + 规格书v1.3.0 + 创作计划v1.0.0 + 30章实际内容*",
      "production_brief": "项目类型：\n\n- 古装女性权谋短剧\n- 重生\n- 宅斗\n- 家族利益博弈\n- 商道权谋\n- 人物之间的试探、隐忍、算计与反击\n\n类型边界：\n\n- “权谋”表示人物关系、利益冲突和叙事节奏。\n- 如原文不存在皇宫、后宫、妃嫔、皇帝或朝廷线，不得擅自增加。\n- 不得为了制造“宫斗感”改变原文世界观和人物身份。\n\n改编方向：\n\n- 真人短剧叙事\n- 冲突清晰\n- 节奏紧凑\n- 情绪递进明确\n- 保留人物核心动机\n- 内心描写优先转化为动作、微表情、停顿、呼吸和视线变化\n- 不得为了追求爽感篡改原文事实\n- 不得确认 unknown_do_not_invent 内容\n\n视觉方向：\n\n- 真人写实风格\n- 古装影视剧质感\n- 真实人物皮肤纹理\n- 真实服饰和织物纹理\n- 低饱和、柔和电影布光\n- 精致但不过度仙侠化\n- 非动漫\n- 非二次元\n- 非游戏建模\n- 场景、服饰和道具符合人物身份及故事环境\n\n生产约束：\n\n- 主要画幅为 16:9\n- 后续 LibTV 视频 Unit 必须为 5–15 秒\n- 人物脸部与骨相保持一致\n- 服装、发型、配饰保持连续\n- 场景布局和家具位置保持一致\n- 人物站位、左右关系和视线保持一致\n- 光源方向和时间状态保持一致\n- 前后视频节点动作必须连续",
      "series_canon": "# 世界观设定\n\n## 元数据\n- **作品**：商海沉浮·釜底抽薪篇\n- **宪法版本**：v2.0.0\n- **创建日期**：2026-06-16\n- **世界观基调**：偏架空爽文（商业逻辑为主，朝堂为背景板）\n- **来源**：规格书澄清#1 + 30章实际内容\n\n---\n\n## 一、时代背景\n\n### 王朝设定\n- **国号**：未命名（架空王朝，不深究历史朝代）\n- **政治结构**：君主制 + 六部制（仿古，不考据具体年代）\n- **核心设定**：商业发达，盐铁等重要物资半官营半私营\n- **特点**：爵位世袭、科举入仕并存；官商合作普遍\n\n### 创作原则\n- 朝堂只是背景板——政治斗争不展开，焦点始终在商战\n- 法律、官职、商业规则服务于故事，不追求历史考据\n- 架空自由度——可以自创商业规则，不需对应真实朝代\n\n---\n\n## 二、政治体系\n\n### 爵位层级（简化版）\n\n| 爵位 | 说明 | 故事中对应 |\n|------|------|----------|\n| 侯府 | 中高层贵族，世袭罔替 | 顾长渊家族 |\n| 丞相府 | 文官之首 | 林婉兮之父（外任中） |\n\n**爵位继承**：\n- 世子是法定继承人\n- 犯罪可被削去世子爵位（顾长渊的结局）\n- 老侯爷在世时，侯府仍由他名义上掌管\n\n### 朝廷六部（简化版）\n\n| 部门 | 职能 | 故事中涉及 |\n|------|------|----------|\n| 户部 | 财政、漕运、盐铁、税收 | 核心舞台 |\n| 吏部 | 官员任免 | 间接涉及（张侍郎） |\n| 工部 | 工程、河道 | 间接涉及（林老板的河道工程） |\n\n### 户部官僚层级（故事实际出现）\n\n| 职位 | 品级 | 职能 | 代表人物 |\n|------|------|------|---------|\n| 户部侍郎 | 三品 | 户部二把手，主持审判 | 审判顾长渊 |\n| 户部郎中 | 五品 | 司局长官 | 顾长渊的目标职位 |\n| 户部主事 | 六品 | 处级官员 | 王主事 |\n| 户部员外郎 | 从五品 | 司局副职 | 陈员外郎 |\n| 户部书办 | 不入流 | 管账的文书吏 | 周书办（二十年老吏） |\n\n**官职体系说明**：\n- 郎中是实权职位，管一司事务\n- 书办虽无品级，但掌握账目命脉，实际权力不小\n- 进入六部需要\"运作\"——送礼、攀关系、找引荐人\n\n---\n\n## 三、商业体系\n\n### 货币政策\n\n| 单位 | 说明 | 实际购买力参考 |\n|------|------|-------------|\n| 文 | 铜钱，最小单位 | 1斤灰盐=15文；1斤雪盐=40文 |\n| 两（银子） | 银两，基本交易单位 | 1两≈1000文；一个人月钱约3-5两 |\n| 银票 | 钱庄发行的纸币 | 大额交易用，京城最大钱庄最可信 |\n\n**购买力锚定**：\n- 一个盐铺二掌柜月钱：数两银子\n- 漕运批文转让价：1800两\n- 渣男挪用户部公款总额：13000两（足以发配三千里）\n- 侯府中人二十年积蓄：500两\n\n### 钱庄制度\n- 京城有主要钱庄若干，最大的那家信誉最高\n- 银票可跨城兑现\n- 钱庄也做借贷（有利息，连本带利）\n- 借据（借据）具有法律效力\n\n### 盐业体系\n\n#### 盐的种类与等级\n\n| 品种 | 品质 | 价格 | 说明 |\n|------|------|------|------|\n| 灰盐 | 低 | 15文/斤 | 普通百姓用盐，颜色灰暗 |\n| 青盐 | 中 | 30文/斤 | 好盐，市面主流 |\n| 雪盐 | 高 | 40文/斤 | 沈清荷的技术创新，纯白如雪 |\n\n#### 制盐技术（实际设定）\n- **传统工艺**：卤水熬煮，产出灰盐或青盐\n- **豆浆法（核心创新）**：在卤水中加豆浆，杂质随豆浆沫浮出，撇去后得到纯白结晶\n- **来源**：南方一本杂记中记载的民间偏方（沈清荷前世记忆）\n- **技术壁垒**：简单但没人知道——信息差就是商业优势\n\n#### 盐铁渠道（权力结构）\n- 盐作为必需品商品，由政府控制流通\n- 贵族和官员可以通过\"关系\"获得盐的经营权\n- 侯府掌握盐铺——这是一种权力资源\n- 变相垄断：有权有势者垄断最好的渠道\n\n#### 盐引制度\n- 盐引是政府颁发的食盐经营许可证\n- 持有盐引者可合法经营食盐\n- 皇商资格是最高级别的盐引\n\n### 漕运体系\n\n#### 漕运（运河运输系统）\n- 政府控制的粮食物资运输网络\n- 核心路线：江淮→京城（运河沿线）\n\n#### 供应商准入\n- 需要\"供应商资格\"（批文），有限额——\"一个萝卜一个坑\"\n- 获得方式：购买、继承、或者通过关系运作\n- 转让价格：1800两左右（故事中马老板卖批文的价格）\n\n#### 运营成本\n- 租船费 + 雇船工 + 码头仓库租赁 + 沿途关卡过路费\n- 一条批文年收入可达上万两\n- 但前期投入大，现金流压力重\n\n#### 盈利模式\n- 政府支付固定运费\n- 同时可夹带部分私货（灰色地带）\n- 关键在于压低运营成本\n\n### 其他主要产业\n\n| 产业 | 经营模式 | 故事中涉及 |\n|------|---------|----------|\n| 南货（金陵） | 丝绸、茶叶、干货 | 第4章截胡的第一单 |\n| 粮食 | 城中有多家粮商 | 刘德旺的粮铺 |\n| 木材 | 河道工程 | 渣男帮林老板拿河道工程 |\n| 丝绸 | 西城多家铺子 | 吴老板是侯府远亲 |\n| 杂货 | 油盐酱醋 | 王掌柜的王家杂货铺 |\n\n### 商业规则\n\n#### 账目制度\n- 店铺必须记流水账（流水账）\n- 账目分类：进项（收入）、支出、\"特定\"（指定用途）、\"杂项\"、\"人情往来\"、\"采买\"、\"其他\"\n- \"特定\"和\"杂项\"是常见的造假科目（顾长渊即在此做手脚）\n- 账册可作为法律证据\n\n#### 合伙方式\n- 五五分账（最常见）\n- 干股（不出钱只出人/技术，按约定比例分利润）\n- 合伙契书：写明投入、分成、退出条件\n- 沈清荷的合伙人模式：她出资金和销路，陈伯远出技术，五五分\n\n#### 统一定价策略\n- 沈清荷的雪盐统一零售价40文/斤\n- 避免各铺子恶性竞价\n- 树立品牌形象：雪盐=好盐=贵得有道理\n\n#### 中介（掮客）体系\n- 东市等地有专门的中介人\n- 撮合买卖双方，收取佣金\n- 孙旺财是典型的中介：人脉广但不专，谁给钱帮谁\n\n---\n\n## 四、社会结构\n\n### 阶层\n| 阶层 | 代表 | 特征 |\n|------|------|------|\n| 贵族 | 侯府、丞相府 | 世袭爵位，有特权 |\n| 官员 | 户部侍郎、书办 | 有实权但非世袭 |\n| 商人 | 沈家、刘德旺 | 有钱但地位低 |\n| 手艺人 | 陈伯远 | 凭手艺吃饭 |\n| 平民 | 赵四一家 | 工薪阶层 |\n\n### 商人的社会地位\n- 重农抑商的传统仍在，商人有钱但没地位\n- 商人通过与贵族联姻来\"洗白\"身份——顾长渊与沈清荷的婚约本质是侯府拿爵位换沈家财富\n- 皇商资格算是商人的最高荣誉（沈清荷第29章获得）\n\n### 女性的社会处境\n- 未出阁的姑娘主要职责：嫁人\n- 管理家族生意是例外（因沈家父母不在/无能，姐妹当家）\n- 女子书院是突破性的新事物（沈清莲第29章创办）\n- 清莲书院的核心理念：\"读书不是为了嫁人。是为了让你们以后——有的选。\"\n\n---\n\n## 五、婚约与法律\n\n### 婚约制度\n- 议亲（谈婚论嫁）→ 定亲 → 婚约成立\n- 婚书是正式文书，红纸黑字，盖双方家族印章\n- 毁约需要正当理由（如一方犯罪被削爵——沈清荷以此为由撕毁婚书）\n\n### 司法制度（简化）\n\n**举报途径**：\n- 匿名信可以触发调查（沈清荷向户部侍郎送匿名信）\n- 附带证据的举报更有分量\n- 门房接收信件后层层传递\n\n**审判程序**：\n- 户部大堂审理（第25章）\n- 原告方出示证据\n- 被告方认罪或辩护\n- 数罪并罚\n\n**刑罚体系**：\n| 罪行 | 惩罚 |\n|------|------|\n| 挪用户部公款 | 革职 + 发配充军 |\n| 伪造账目 | 计入从重情节 |\n| 贪墨铺银 | 削去爵位 |\n| 贪污万两以上 | 发配三千里，终身不得回京 |\n| 数罪并罚 | 叠加处罚 |\n\n---\n\n## 六、地理环境\n\n### 京城及周边\n\n```\n                        北疆（流放地）\n                           ↕ 数千里\n                        京城（核心舞台）\n                       ↙  ↓  ↘\n               西城区   皇城区   东城区\n              (李府等)  (户部等)  (东市/码头/\n                                   运河/书院)\n                           ↓\n                        江淮地区\n                        (运河沿线)\n                           ↓\n                        金陵（南京）\n                   （南货集散地，两天路程）\n                           ↓\n                        江南\n                  （沈家庄园、方先生故地）\n```\n\n### 主要地点汇总\n\n#### 沈家\n- 书房（沈清荷的核心场景）：窗户对着桂花树，有暗格藏漕运批文\n- 后院亭子：姐妹饮酒、会客、最终场景\n- 海棠树：婚约灰烬最终撒落之处\n- 厅堂：接待客人、烧毁婚书\n\n#### 侯府\n- 书房（顾长渊的核心场景）\n- 盐铺（最大的那家）：赵四在此工作\n- 侧门/巷子：渣男的秘密出入通道\n\n#### 商业区\n- 东市：掮客活跃、王家杂货铺所在地\n- 码头：城东运河边，漕运装卸处\n- 城东运河边：陈伯远扩建后的新作坊\n\n#### 官署\n- 户部大堂：审判场所\n- 户部侧厢房：周书办工作处\n- 户部门房值班室：匿名信送达处\n\n#### 社交场所\n- 城西李府：赏花宴\n- 张侍郎府：赏春宴\n- 锦绣阁（东城丝绸铺）：沈清莲与王夫人的偶遇地点\n\n#### 女性事业空间\n- 清莲书院（东城）：前退休官员旧宅，院里有槐树\n- 陈伯远盐坊（城外→运河边）：从小作坊到大工场\n\n---\n\n## 七、文化习俗\n\n### 社交礼仪\n- 初次见面递\"帖子\"（名帖）\n- 做客带礼物（绸料等）\n- 社交场合：赏花宴、赏春宴是核心社交场景\n- 贵妇圈是信息流通渠道——沈清莲的主要战场\n\n### 送礼文化\n- 桂花糕（天香楼）：男女之间送，有暧昧意味\n- 龙井茶（上等）：顾长渊案发时出现在书房，是姐妹的暗示\n- 桂花酒（自酿）：沈清莲三顾茅庐请方先生的诚意\n- 绸料：社交场合的标准伴手礼\n\n### 时间标记\n- 故事时间跨度：约一年（春天→次年春/夏）\n- 月份：正月、三月、四月、五月、六月均有出现\n- 花卉轮回：桂花打苞→满开→花落；海棠花开花谢；牡丹盛开\n\n---\n\n## 八、经济世界观核心规则\n\n### 1. 信息差即为权力\n- 沈清荷利用前世记忆知道漕运批文要转手\n- 沈清莲知道每个人的软肋和秘密\n- \"豆浆法\"在书中就有，但别人不知道\n- 姐妹的复仇本质：用信息差碾压权力差\n\n### 2. 账目即为武器\n- 每一笔账都是证据\n- 沈清荷的账本记录了渣男全部罪行\n- \"特定\"、\"杂项\"是贪污的入口\n- 账目可以在公堂上作为呈堂证供\n\n### 3. 渠道即为命脉\n- 控制渠道等于控制市场\n- 盐铁渠道被侯府垄断 → 沈清荷开辟雪盐渠道 → 架空侯府\n- 漕运渠道是渣男的大计划 → 姐妹从中设陷阱\n- 粮食渠道被策反 → 渣男断供\n\n### 4. 人情即为资本\n- 沈清莲的核心竞争力\n- 记住每个人的软肋和欲望 → 精准策反\n- 真诚对待赵四、刘德旺 → 建立非交易性信任\n- 债主对渣男不好 ≠ 盟友对姐妹好，关键在\"怎么对待人\"\n\n---\n\n## 九、写作约束\n\n### 世界观的\"留白\"策略\n- 不交代王朝的具体国号、帝号——因为不重要\n- 不细说六部运作的细节——需要什么设定什么\n- 不展开朝堂政治——始终以商业博弈为主\n- 不加入魔法/修仙/系统——纯现实商战（虽然架空）\n\n### 架空爽文的自由度\n- 可以自创商业规则、法律条文、官职体系\n- 不需要严格考据历史——因为本来就不是历史小说\n- 逻辑自洽 > 历史真实\n- 爽感优先——但要在逻辑合理的范围内\n\n---\n\n*创建时间：2026-06-16*\n*基于：规格书v1.3.0 + 创作计划v1.0.0 + 30章实际内容*\n*宪法合规：偏架空爽文（澄清#1），朝堂为背景板*",
      "source_run_id": "b360d68e225c4e6da68f491d5d044024",
      "source_script_approval_record": {
        "action": "script_approved",
        "artifact_id": "shengsi-chapter-001",
        "created_at": "2026-06-28T12:48:03.895524Z",
        "note": "",
        "record_id": "191fd857c39147108ace296578e3bc7b",
        "reviewer": "verifier",
        "revision_id": "c37329ee465c464b99bc5a57b690983f",
        "sequence": 1
      },
      "source_script_approval_record_id": "191fd857c39147108ace296578e3bc7b",
      "source_script_artifact_id": "shengsi-chapter-001",
      "source_script_content_hash": "ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a",
      "source_script_markdown": "# Mock Drama Script Revision\n\nruntime_model: mock-script\nsource_basis: manifest\n\n## Scene: 1-1\n\n【画面】\n女主在清晨醒来，意识到命运重启。\n\n【动作】\n她检查身边物件，确认眼前不是幻觉。\n\n【台词】\n女主：这一世，我要先看清局。\n\n## Scene: 1-2\n\n【画面】\n账册摊开，旧日线索重新浮现。\n\n【动作】\n她整理证据，把危险关系和家族账目分开标记。\n\n【台词】\n女主：账不会骗人，人心才会。\n",
      "source_script_revision_id": "c37329ee465c464b99bc5a57b690983f"
    },
    "output_contract": {
      "format": "markdown",
      "parser_version": "storyboard-markdown-v1",
      "profile": "storyboard-markdown-mvp-v1",
      "supported_artifacts": [
        "storyboard_markdown"
      ],
      "unsupported_bundle_artifacts": [
        "storyboard_json_bundle",
        "shot_prompt_package",
        "visual_asset_binding_package",
        "libtv_execution_package",
        "agnes_execution_package"
      ]
    },
    "request_format_version": "runtime-request-v1",
    "runtime_config": {
      "model": "mock-storyboard",
      "provider": "mock",
      "timeout_seconds": 60
    },
    "skill": {
      "execution_profile": "storyboard-markdown-mvp-v1",
      "package_hash": "347b27cfeb0b08c7d1acf825daacd6723f194d933ed34c0bdd18d821f3478230",
      "skill_id": "ai-drama-storyboard-design-skill",
      "version": "v0.1.0"
    },
    "skill_instruction": {
      "content": "# AI Drama Storyboard Design Skill v0.1.0\n\n## Purpose\n\nConvert an approved drama script revision into a creator-facing storyboard revision with shot-level continuity, source coverage, and approval traceability.\n\n## Scope\n\nUse only for storyboard design. Do not emit shot prompts, LibTV packages, visual asset plans, image/video prompts, or execution commands.\n\n## Required Inputs\n\n- approved script revision\n- source approval record\n- `series_canon`\n- `characters`\n- `production_brief`\n\n## Markdown Contract\n\n- Top header: `# Storyboard`\n- Scene header: `## 场次：{scene_id}`\n- Shot header: `### 镜头 {shot_order}`\n- Every shot must include:\n  - `scene_id`\n  - `shot_id`\n  - `shot_order`\n  - `source_scene_reference`\n  - `duration_seconds`\n  - `shot_size`\n  - `camera_angle`\n  - `camera_movement`\n  - `visual_composition`\n  - `character_positions`\n  - `character_actions`\n  - `emotion_performance`\n  - `dialogue`\n  - `sound_notes`\n  - `continuity_in`\n  - `continuity_out`\n\n## Rules\n\n- Preserve source scene order and source facts.\n- Do not add new core plot events.\n- Every shot duration must be 5-15 seconds.\n- Every scene shot must bind a stable `source_scene_reference`.\n- `shot_id` must be stable within the chapter and unique per shot.\n- `shot_order` must be unique and strictly increasing within each scene.\n- `continuity_in` and `continuity_out` must describe the immediate transition state.\n- `character_positions`, `character_actions`, and `emotion_performance` must be explicit for every shot.\n- Do not mention downstream execution artifacts or terms.\n\n## Output\n\nWrite creator-facing Markdown storyboard only.\n",
      "relative_path": "SKILL.md",
      "sha256": "9eeb47b0494816df974cf44f4b535b89600387e1160041cbe97a4af71537df2b"
    },
    "system_instruction": "Follow the skill package and return only the requested Markdown Storyboard revision."
  }
}

## 6. Validator Matrix
{
  "storyboard_structure": {
    "validator_id": "storyboard_structure",
    "status": "PASS",
    "required": true,
    "exit_code": 0,
    "error_code": "",
    "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"storyboard structure valid\", \"scenes\": 2}\n",
    "stderr": "",
    "report": {
      "final_status": "pass",
      "error_code": "",
      "message": "storyboard structure valid",
      "scenes": 2
    }
  },
  "storyboard_duration": {
    "validator_id": "storyboard_duration",
    "status": "PASS",
    "required": true,
    "exit_code": 0,
    "error_code": "",
    "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"duration valid\", \"durations\": [6, 7, 8, 6], \"shot_count\": 4}\n",
    "stderr": "",
    "report": {
      "final_status": "pass",
      "error_code": "",
      "message": "duration valid",
      "durations": [
        6,
        7,
        8,
        6
      ],
      "shot_count": 4
    }
  },
  "storyboard_source_coverage": {
    "validator_id": "storyboard_source_coverage",
    "status": "PASS",
    "required": true,
    "exit_code": 0,
    "error_code": "",
    "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"source coverage valid\", \"source_scene_references\": [\"1-1\", \"1-1\", \"1-2\", \"1-2\"], \"missing_scene_references\": [], \"extra_scene_references\": []}\n",
    "stderr": "",
    "report": {
      "final_status": "pass",
      "error_code": "",
      "message": "source coverage valid",
      "source_scene_references": [
        "1-1",
        "1-1",
        "1-2",
        "1-2"
      ],
      "missing_scene_references": [],
      "extra_scene_references": []
    }
  },
  "storyboard_continuity": {
    "validator_id": "storyboard_continuity",
    "status": "PASS",
    "required": true,
    "exit_code": 0,
    "error_code": "",
    "stdout": "{\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"continuity valid\", \"shot_count\": 4}\n",
    "stderr": "",
    "report": {
      "final_status": "pass",
      "error_code": "",
      "message": "continuity valid",
      "shot_count": 4
    }
  },
  "genericity": {
    "validator_id": "genericity",
    "status": "NOT_APPLICABLE",
    "required": false,
    "exit_code": 0,
    "error_code": "",
    "stdout": "",
    "stderr": "validator applies to skill_package, not current revision type storyboard_revision\n",
    "report": {}
  }
}

## 7. Source Coverage
{
  "SOURCE_SCRIPT_SCENES": [
    "1-1",
    "1-2"
  ],
  "STORYBOARD_SOURCE_REFERENCES": [
    "1-1",
    "1-1",
    "1-2",
    "1-2"
  ],
  "MISSING_SOURCE_SCENES": [],
  "EXTRA_SOURCE_REFERENCES": [],
  "ORDER_MISMATCH": false
}

## 8. Lineage and Provenance
{
  "source_revision_id": "c37329ee465c464b99bc5a57b690983f",
  "source_content_hash": "ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a",
  "captured_approval_record_id": "191fd857c39147108ace296578e3bc7b",
  "export_sidecar": {
    "approval_record": {
      "action": "storyboard_approved",
      "artifact_id": "shengsi-chapter-001:storyboard",
      "created_at": "2026-06-28T12:48:04.033578Z",
      "note": "",
      "record_id": "1dd2a4d0b8ce49cd82493a1e01c95157",
      "reviewer": "verifier",
      "revision_id": "ef108da52ae9408dbd58ebbb7b9f67b8",
      "sequence": 2
    },
    "artifact_id": "shengsi-chapter-001:storyboard",
    "content_hash": "e08a5f1a084858662578029458b2b036217c814b678be264f57340a29a6b78f8",
    "export_time": "2026-06-28T12:48:04.034816Z",
    "freshness_status": "FRESH",
    "input_references": [
      {
        "logical_type": "characters",
        "relative_path": "characters.md",
        "sha256": "1df41598fa2a0786c90539979c076cce950325ffed0e8e2c27de37657b6839fc"
      },
      {
        "logical_type": "production_brief",
        "relative_path": "production-brief.md",
        "sha256": "8cbb61658176274e05681bac6769fabba5c8dd1eee14c0600db4b1a5dbc74f0d"
      },
      {
        "logical_type": "series_canon",
        "relative_path": "series-canon.md",
        "sha256": "39da5039ea9aa3ff2fcc020278ad07db29d5eec3c042595171f26f08d98f138b"
      },
      {
        "logical_type": "source_revision",
        "relative_path": "c37329ee465c464b99bc5a57b690983f",
        "sha256": "ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a"
      },
      {
        "logical_type": "source_script_approval",
        "relative_path": "c37329ee465c464b99bc5a57b690983f",
        "sha256": "3dd9dd7ea205cfcb7dbb4d0b289e9a33f0fa88e55d1f710935d3d3a00059ba04"
      }
    ],
    "model": "mock-storyboard",
    "package_hash": "347b27cfeb0b08c7d1acf825daacd6723f194d933ed34c0bdd18d821f3478230",
    "provider": "mock",
    "request_hash": "090b8000962d926f21fa73296cfda66497b487f5095127de3b35edce8382783c",
    "revision_id": "ef108da52ae9408dbd58ebbb7b9f67b8",
    "run_id": "4f9fd9dca391441a8d8f812dcd3bef52",
    "skill_id": "ai-drama-storyboard-design-skill",
    "skill_version": "v0.1.0",
    "source_approval_record": {
      "action": "script_approved",
      "artifact_id": "shengsi-chapter-001",
      "created_at": "2026-06-28T12:48:03.895524Z",
      "note": "",
      "record_id": "191fd857c39147108ace296578e3bc7b",
      "reviewer": "verifier",
      "revision_id": "c37329ee465c464b99bc5a57b690983f",
      "sequence": 1
    },
    "source_revision_id": "c37329ee465c464b99bc5a57b690983f",
    "source_script_approval_record_id": "191fd857c39147108ace296578e3bc7b",
    "source_script_artifact_id": "shengsi-chapter-001",
    "source_script_content_hash": "ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a",
    "source_script_revision_id": "c37329ee465c464b99bc5a57b690983f"
  }
}

## 9. Staleness
{
  "script_a_revision_id": "bf2ebcbf8d504f29b2ad98d8f9e38538",
  "script_b_revision_id": "f40d6acb26b7401b9b85c5f75993e66d",
  "storyboard_a1_revision_id": "17db560768204078915247b0770a7be1",
  "storyboard_a1_freshness_after_b": "STALE",
  "storyboard_a1_source_revision_id": "bf2ebcbf8d504f29b2ad98d8f9e38538",
  "storyboard_a1_source_approval_record": {
    "sequence": 1,
    "record_id": "422eb97edf77446793be11ba30625858",
    "revision_id": "bf2ebcbf8d504f29b2ad98d8f9e38538",
    "artifact_id": "shengsi-chapter-001",
    "action": "script_approved",
    "reviewer": "verifier",
    "note": "",
    "created_at": "2026-06-28T12:48:04.100506Z"
  }
}

## 10. Database Compatibility
{
  "fresh_db": {
    "status": "PASS",
    "db_path": "/tmp/ai-drama-storyboard-complete-verification/runtime.db"
  },
  "restart": {
    "status": "PASS",
    "freshness_after_restart": "FRESH"
  },
  "resource_close": {
    "status": "PASS",
    "sqlite_lock_resolved": true
  }
}

## 11. Findings
[]

## 12. Final Record Table
[
  {
    "test_item": "Migration Verify",
    "status": "PASS",
    "evidence": "{\n  \"status\": \"valid\",\n  \"checked_files\": 81\n}"
  },
  {
    "test_item": "PyCompile",
    "status": "PASS",
    "evidence": ""
  },
  {
    "test_item": "Direct Pytest",
    "status": "PASS",
    "evidence": "{\"summary\": {\"passed\": 92, \"skipped\": 0}, \"stdout\": \"........................................................................ [ 78%]\\n....................                                                     [100%]\\n92 passed in 25.18s\"}"
  },
  {
    "test_item": "Verifier Inner Pytest",
    "status": "PASS",
    "evidence": "{\"summary\": {\"passed\": 91, \"skipped\": 1}, \"skip_reason\": \"recursive self-test guard\", \"stdout\": \"..s..................................................................... [ 78%]\\n....................                                                     [100%]\\n=========================== short test summary info ============================\\nSKIPPED [1] tests/acceptance/test_storyboard_workflow_acceptance.py:23: skip recursive self-test inside verification entrypoint\\n91 passed, 1 skipped in 12.36s\"}"
  },
  {
    "test_item": "Skill Package",
    "status": "PASS",
    "evidence": "{\"script\": {\"skill_ref\": \"ai-drama-script-adaptation-skill@v0.6.1-rc2.4\", \"version\": \"v0.6.1-rc2.4\", \"content_hash\": \"b38eae160957484c68b7d47973a8b45419266d33c83b35de91be7291679d845f\"}, \"storyboard\": {\"skill_ref\": \"ai-drama-storyboard-design-skill@v0.1.0\", \"version\": \"v0.1.0\", \"execution_profile\": \"storyboard-markdown-mvp-v1\", \"input_types\": [\"approved_script_revision\"], \"output_types\": [\"storyboard_revision\"], \"required_validators\": [\"storyboard_structure\", \"storyboard_duration\", \"storyboard_source_coverage\", \"storyboard_continuity\"], \"package_hash\": \"347b27cfeb0b08c7d1acf825daacd6723f194d933ed34c0bdd18d821f3478230\", \"support_files\": [\"validators/common.py\"], \"context_files\": [\"README.md\", \"CHANGELOG.md\", \"MIGRATION-NOTES.md\", \"requirements.txt\", \"references/storyboard-rules.md\", \"references/source-staleness-policy.md\", \"references/shot-boundary-policy.md\", \"references/continuity-policy.md\", \"templates/storyboard-outline.template.md\", \"templates/storyboard-outline.template.json\", \"schemas/storyboard-outline.schema.json\", \"schemas/storyboard-coverage.schema.json\", \"contracts/storyboard-design-contract-v1.md\", \"contracts/storyboard-approval-contract-v1.md\", \"runtime-validators/forbidden-terms.txt\"]}}"
  },
  {
    "test_item": "CLI Input Gate",
    "status": "PASS",
    "evidence": "{\"script_run_id\": \"b360d68e225c4e6da68f491d5d044024\", \"storyboard_run_id\": \"4f9fd9dca391441a8d8f812dcd3bef52\"}"
  },
  {
    "test_item": "Source Approval Gate",
    "status": "PASS",
    "evidence": "{\"sequence\": 1, \"record_id\": \"191fd857c39147108ace296578e3bc7b\", \"revision_id\": \"c37329ee465c464b99bc5a57b690983f\", \"artifact_id\": \"shengsi-chapter-001\", \"action\": \"script_approved\", \"reviewer\": \"verifier\", \"note\": \"\", \"created_at\": \"2026-06-28T12:48:03.895524Z\"}"
  },
  {
    "test_item": "Context Gate",
    "status": "PASS",
    "evidence": "{\"context_files\": [{\"content\": \"# AI Drama Storyboard Design Skill\\n\\nFormal storyboard design package for approved drama script revisions.\\n\", \"logical_type\": \"context\", \"relative_path\": \"README.md\", \"sha256\": \"44690a2d7fc41955720c48da7b6f2dc8de7d006e58d8defbf6fc7e06fa820cc7\"}, {\"content\": \"# Changelog\\n\\n## v0.1.0\\n\\n- Initial formal storyboard skill package.\\n\", \"logical_type\": \"context\", \"relative_path\": \"CHANGELOG.md\", \"sha256\": \"c2b46e2c1f025cb305329d43fdc8ce33dca2a66ea7c4a8e78eb6e465e28478fc\"}, {\"content\": \"# Migration Notes\\n\\nThis package is newly created from approved storyboard requirements.\\nIt is not a migration of an existing formal Storyboard Skill.\\n\", \"logical_type\": \"context\", \"relative_path\": \"MIGRATION-NOTES.md\", \"sha256\": \"77ccd75901e97c91ad276967a0749753a4a17a84a085ef78a7ecad31d6714ad4\"}, {\"content\": \"PyYAML>=6.0\\n\", \"logical_type\": \"context\", \"relative_path\": \"requirements.txt\", \"sha256\": \"71749243f84428fee225bfaa796dca5ef6c1e83a98f6d2a407df615b0390d6fb\"}, {\"content\": \"# Storyboard Rules\\n\\nStoryboard revisions must preserve approved script scene order, shot continuity, and upstream binding.\\n\", \"logical_type\": \"context\", \"relative_path\": \"references/storyboard-rules.md\", \"sha256\": \"11ad719d044211bcd298fa5cd35123988afd30f9ebd564cee6c4f950049cee43\"}, {\"content\": \"# Source Staleness Policy\\n\\nA storyboard revision becomes stale when its source script revision is no longer the current approved revision for the source script artifact.\\n\", \"logical_type\": \"context\", \"relative_path\": \"references/source-staleness-policy.md\", \"sha256\": \"bd735f285125608e74eb9d023b9ffc10ebbc49774a5430d0a243a55169133338\"}, {\"content\": \"# Shot Boundary Policy\\n\\nSplit scenes into shots using stable, source-grounded boundaries.\\n\", \"logical_type\": \"context\", \"relative_path\": \"references/shot-boundary-policy.md\", \"sha256\": \"cd746dd92e506bffb2e5254d8fdffed7287af362e3c828170c3ddd1e0474ff51\"}, {\"content\": \"# Continuity Policy\\n\\nEach shot must record continuity_in and continuity_out values.\\n\", \"logical_type\": \"context\", \"relative_path\": \"references/continuity-policy.md\", \"sha256\": \"d3996b21606e8eabe3ddeef8a6a36f41616916424b3740d5f2d600d37ba7b5d1\"}, {\"content\": \"# Storyboard\\n\\n## 场次：{scene_id}\\n\\n### 镜头 {shot_order}\\n\\n- scene_id: {scene_id}\\n- shot_id: {shot_id}\\n- shot_order: {shot_order}\\n- source_scene_reference: {source_scene_reference}\\n- duration_seconds: {duration_seconds}\\n- shot_size: {shot_size}\\n- camera_angle: {camera_angle}\\n- camera_movement: {camera_movement}\\n- visual_composition: {visual_composition}\\n- character_positions: {character_positions}\\n- character_actions: {character_actions}\\n- emotion_performance: {emotion_performance}\\n- dialogue: {dialogue}\\n- sound_notes: {sound_notes}\\n- continuity_in: {continuity_in}\\n- continuity_out: {continuity_out}\\n\", \"logical_type\": \"context\", \"relative_path\": \"templates/storyboard-outline.template.md\", \"sha256\": \"38bda79d09c72a227d78757c9645a060986fd6c085fea79abbf5369ac38df22c\"}, {\"content\": \"{\\n  \\\"scene_id\\\": \\\"{scene_id}\\\",\\n  \\\"shots\\\": [\\n    {\\n      \\\"scene_id\\\": \\\"{scene_id}\\\",\\n      \\\"shot_id\\\": \\\"{shot_id}\\\",\\n      \\\"shot_order\\\": \\\"{shot_order}\\\",\\n      \\\"source_scene_reference\\\": \\\"{source_scene_reference}\\\",\\n      \\\"duration_seconds\\\": \\\"{duration_seconds}\\\",\\n      \\\"shot_size\\\": \\\"{shot_size}\\\",\\n      \\\"camera_angle\\\": \\\"{camera_angle}\\\",\\n      \\\"camera_movement\\\": \\\"{camera_movement}\\\",\\n      \\\"visual_composition\\\": \\\"{visual_composition}\\\",\\n      \\\"character_positions\\\": \\\"{character_positions}\\\",\\n      \\\"character_actions\\\": \\\"{character_actions}\\\",\\n      \\\"emotion_performance\\\": \\\"{emotion_performance}\\\",\\n      \\\"dialogue\\\": \\\"{dialogue}\\\",\\n      \\\"sound_notes\\\": \\\"{sound_notes}\\\",\\n      \\\"continuity_in\\\": \\\"{continuity_in}\\\",\\n      \\\"continuity_out\\\": \\\"{continuity_out}\\\"\\n    }\\n  ]\\n}\\n\", \"logical_type\": \"context\", \"relative_path\": \"templates/storyboard-outline.template.json\", \"sha256\": \"b9d519cd06e68382550ed862e8f8f5ab32dc9d45cbccf3d208899fb5c4efafb9\"}, {\"content\": \"{\\n  \\\"$schema\\\": \\\"https://json-schema.org/draft/2020-12/schema\\\",\\n  \\\"type\\\": \\\"object\\\",\\n  \\\"required\\\": [\\\"scene_id\\\", \\\"shots\\\"],\\n  \\\"additionalProperties\\\": false,\\n  \\\"properties\\\": {\\n    \\\"scene_id\\\": {\\n      \\\"type\\\": \\\"string\\\",\\n      \\\"minLength\\\": 1\\n    },\\n    \\\"shots\\\": {\\n      \\\"type\\\": \\\"array\\\",\\n      \\\"minItems\\\": 1,\\n      \\\"items\\\": {\\n        \\\"type\\\": \\\"object\\\",\\n        \\\"required\\\": [\\n          \\\"scene_id\\\",\\n          \\\"shot_id\\\",\\n          \\\"shot_order\\\",\\n          \\\"source_scene_reference\\\",\\n          \\\"duration_seconds\\\",\\n          \\\"shot_size\\\",\\n          \\\"camera_angle\\\",\\n          \\\"camera_movement\\\",\\n          \\\"visual_composition\\\",\\n          \\\"character_positions\\\",\\n          \\\"character_actions\\\",\\n          \\\"emotion_performance\\\",\\n          \\\"dialogue\\\",\\n          \\\"sound_notes\\\",\\n          \\\"continuity_in\\\",\\n          \\\"continuity_out\\\"\\n        ],\\n        \\\"additionalProperties\\\": false,\\n        \\\"properties\\\": {\\n          \\\"scene_id\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"shot_id\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"shot_order\\\": {\\\"type\\\": \\\"integer\\\", \\\"minimum\\\": 1},\\n          \\\"source_scene_reference\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"duration_seconds\\\": {\\\"type\\\": \\\"integer\\\", \\\"minimum\\\": 5, \\\"maximum\\\": 15},\\n          \\\"shot_size\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"camera_angle\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"camera_movement\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"visual_composition\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"character_positions\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"character_actions\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"emotion_performance\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"dialogue\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"sound_notes\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"continuity_in\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"continuity_out\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1}\\n        }\\n      }\\n    }\\n  }\\n}\\n\", \"logical_type\": \"context\", \"relative_path\": \"schemas/storyboard-outline.schema.json\", \"sha256\": \"66bd14811036d2214979607f261da406b40efcbc77bd768c2f0263cc9ab04895\"}, {\"content\": \"{\\n  \\\"$schema\\\": \\\"https://json-schema.org/draft/2020-12/schema\\\",\\n  \\\"type\\\": \\\"object\\\",\\n  \\\"required\\\": [\\\"source_scene_references\\\", \\\"missing_scene_references\\\", \\\"extra_scene_references\\\"],\\n  \\\"additionalProperties\\\": false,\\n  \\\"properties\\\": {\\n    \\\"source_scene_references\\\": {\\n      \\\"type\\\": \\\"array\\\",\\n      \\\"items\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n      \\\"minItems\\\": 1,\\n      \\\"uniqueItems\\\": true\\n    },\\n    \\\"missing_scene_references\\\": {\\n      \\\"type\\\": \\\"array\\\",\\n      \\\"items\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n      \\\"uniqueItems\\\": true\\n    },\\n    \\\"extra_scene_references\\\": {\\n      \\\"type\\\": \\\"array\\\",\\n      \\\"items\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n      \\\"uniqueItems\\\": true\\n    }\\n  }\\n}\\n\", \"logical_type\": \"context\", \"relative_path\": \"schemas/storyboard-coverage.schema.json\", \"sha256\": \"6814495e8fd2da8c07670aa09ef6b9d68c59000087ccf0116a676c6757e299a8\"}, {\"content\": \"# Storyboard Design Contract v1\\n\\n## Structure\\n\\n- Markdown only\\n- `# Storyboard` title\\n- `## 场次：{scene_id}` per scene\\n- `### 镜头 {shot_order}` per shot\\n\\n## Required shot fields\\n\\nEach shot must define:\\n\\n- `scene_id`\\n- `shot_id`\\n- `shot_order`\\n- `source_scene_reference`\\n- `duration_seconds`\\n- `shot_size`\\n- `camera_angle`\\n- `camera_movement`\\n- `visual_composition`\\n- `character_positions`\\n- `character_actions`\\n- `emotion_performance`\\n- `dialogue`\\n- `sound_notes`\\n- `continuity_in`\\n- `continuity_out`\\n\\n## Constraints\\n\\n- `duration_seconds` must be between 5 and 15.\\n- `shot_id` must be unique across the chapter.\\n- `shot_order` must be unique within a scene and increase monotonically.\\n- `source_scene_reference` must cover every source scene without inventing new scenes.\\n- No downstream execution terms, shot prompt packages, or platform parameters.\\n\\n## Source binding\\n\\nStoryboard revisions must cite the approved source script revision and its captured approval record in provenance.\\n\", \"logical_type\": \"context\", \"relative_path\": \"contracts/storyboard-design-contract-v1.md\", \"sha256\": \"4b1c8ceec61fdc99c457fe137dfed4102201ebfad1fdc0b95bcbeb90383238a0\"}, {\"content\": \"# Storyboard Approval Contract v1\\n\\nStoryboard approval is allowed only when:\\n\\n1. the storyboard revision is derived from the current approved script revision;\\n2. all required storyboard validators ran and passed;\\n3. no required validator was incorrectly marked not applicable;\\n4. the source script approval record captured at generation time is preserved in provenance;\\n5. the storyboard revision is fresh against the current approved script revision.\\n\\nApproval actions:\\n\\n- `storyboard_approved`\\n- `storyboard_rejected`\\n\\nApproval must not rewrite source provenance after later script approvals.\\n\", \"logical_type\": \"context\", \"relative_path\": \"contracts/storyboard-approval-contract-v1.md\", \"sha256\": \"dd11e4ef08b73b5bb4ac2cb129b2374c5fd4cae4b54f09b46914cb7ef400d970\"}, {\"content\": \"FORBIDDEN_PROJECT_NAME\\nFORBIDDEN_PROJECT_LINE\\nFIXED_SAMPLE_BEAT_ID\\n\", \"logical_type\": \"context\", \"relative_path\": \"runtime-validators/forbidden-terms.txt\", \"sha256\": \"0bd8c989300737eb12bb061db5c0ea271f5a89a20abc6b728ce1b3c273cdbafa\"}], \"inputs\": {\"characters\": \"# 角色设定档案\\n\\n## 元数据\\n- **作品**：商海沉浮·釜底抽薪篇\\n- **宪法版本**：v2.0.0\\n- **创建日期**：2026-06-16\\n- **基于来源**：宪法、规格书、创作计划、30章实际内容\\n\\n---\\n\\n## 一、主角\\n\\n### 沈清荷（姐姐·商道之刃）\\n\\n#### 基本信息\\n- **身份**：沈家长女，商业掌舵人\\n- **年龄**：约二十岁（及笄之后，议亲阶段）\\n- **父亲**：已故（生前是商人，教沈清荷经商）\\n- **母亲**：未出场（人丁单薄的设定）\\n\\n#### 外貌特征\\n- 手指常年握笔，指间有薄茧\\n- 书房窗外的桂花树是她的精神锚点\\n\\n#### 性格层次\\n\\n**表层（对外）**：\\n- 沉稳、话少、持重\\n- 渣男眼中：\\\"温柔、好哄、听话的未婚妻\\\"\\n\\n**中层（对内）**：\\n- 精于算计、冷静如棋手\\n- 凡事用账本说话\\n- 愤怒时不吼叫，在账本上记一笔\\n\\n**深层（核心）**：\\n- 前世被利用至死，重生后的觉悟：爱情只是工具，财权才是根本\\n- 对妹妹的愧疚与保护欲并存\\n- 复仇不是情绪宣泄，是精心策划的商业战争\\n\\n#### 核心能力\\n- 渠道掌控、资源调配\\n- 对数字和账目过目不忘\\n- 前世掌握盐铁渠道，这一世知道未来十年商业风向\\n- 训练有素的商业直觉\\n\\n#### 标志性行为\\n| 动作 | 触发时机 | 在文中的应用 |\\n|------|---------|------------|\\n| 拨动算盘珠 | 重大决定前 | 第1章、第6章、第20章、第30章 |\\n| 在账本上记一笔 | 愤怒/记仇时 | 反复出现，贯穿全书 |\\n| 给妹妹夹菜 | 开心时 | 姐妹互动场景 |\\n| \\\"这笔账，划不来\\\" | 判断得失时 | 金句模式 |\\n\\n#### 前世经历\\n- 被渣男利用商业才能，帮他平步青云登上户部高位\\n- 被渣男挑拨离间，以为妹妹要毒杀自己\\n- 临死前看到渣男搂着丞相之女林婉兮，亲口承认：\\\"我只是借你们沈家的钱袋子，铺我的青云路。\\\"\\n- 被毒杀而死\\n\\n#### 今世成长弧线\\n\\n| 阶段 | 章节 | 状态 |\\n|------|------|------|\\n| 觉醒期 | 第1-3章 | 从震惊到清醒，与妹妹相认，确立复仇同盟 |\\n| 布局期 | 第4-10章 | 截胡生意、记账、设陷阱，表面演痴情未婚妻 |\\n| 发力期 | 第11-16章 | 改良制盐技术，开辟新渠道，蚕食渣男经济命脉 |\\n| 收网期 | 第17-20章 | 引导渣男入局，伪造投资人，准备证据 |\\n| 决裂期 | 第21-28章 | 送匿名信、当堂对质、撕婚书、烧婚约 |\\n| 终局 | 第29-30章 | 拿下皇商资格，掌管三个盐铺，成为独立女商人 |\\n\\n#### 随身道具\\n- **算盘**（核心道具）：第1章结尾第一次拨动 → 第30章最后放下\\n- **账本**（秘密武器）：记录了渣男每一笔贪污、每一笔借款\\n\\n---\\n\\n### 沈清莲（妹妹·人心之网）\\n\\n#### 基本信息\\n- **身份**：沈家次女，社交操盘手\\n- **年龄**：约十七八岁\\n- **训练经历**：十年\\\"察言观色、撒娇卖痴\\\"的训练（第2章自述）\\n\\n#### 外貌特征\\n- 爱笑，笑容天真烂漫\\n- 随身携带梅花团扇，绣线已有些松了（暗示使用频率之高）\\n\\n#### 性格层次\\n\\n**表层（对外）**：\\n- 天真烂漫、笑语晏晏\\n- 渣男眼中：\\\"崇拜自己的小姨子，好利用\\\"\\n\\n**中层（对内）**：\\n- 通透机敏、话里藏刀\\n- 最擅长用无辜的语气说出最致命的信息\\n- 对姐姐真诚，对敌人演戏\\n\\n**深层（核心）**：\\n- 前世痴迷渣男，被利用后惨死\\n- 重生后最痛的不是被渣男害死，而是前世与姐姐反目\\n- 她的复仇武器不是算盘，是人心\\n\\n#### 核心能力\\n- 人际网络构建、情报收集\\n- 十年社交训练：记住每个人的生辰、软肋和欲望\\n- 前世广结善缘，掌握大量人脉情报\\n- 借力打力——不需要亲自出手，让敌人自相残杀\\n\\n#### 标志性行为\\n| 动作 | 触发时机 | 在文中的应用 |\\n|------|---------|------------|\\n| 团扇掩住嘴角笑意 | 说完致命信息后 | 第3章、第7章、第22章 |\\n| 笑语晏晏，话里藏刀 | 社交场合 | 贯穿全书 |\\n| \\\"哎呀，这可不巧了么\\\" | 算计得逞时 | 金句模式 |\\n| 对姐姐真笑，对敌人假笑 | 角色切换时 | 社交场合与私下对比 |\\n\\n#### 前世经历\\n- 被渣男甜言蜜语蒙蔽，前世与姐姐争风吃醋\\n- 四处炫耀未婚夫深情，结果同样被利用至死\\n- 重生方式：做了一场噩梦，梦中经历了前世的一切\\n\\n#### 今世成长弧线\\n\\n| 阶段 | 章节 | 状态 |\\n|------|------|------|\\n| 觉醒期 | 第1-3章 | 从噩梦中醒来，与姐姐对视即达成默契 |\\n| 布局期 | 第4-10章 | 扮演崇拜渣男的小姨子，散播假消息 |\\n| 发力期 | 第11-16章 | 社交策反，拉拢刘德旺，接触王夫人 |\\n| 收网期 | 第17-20章 | 安排假投资人方老板，信息误导渣男 |\\n| 决裂期 | 第21-28章 | 当面翻脸，公开揭露渣男真面目 |\\n| 终局 | 第29-30章 | 创办清莲书院，三顾茅庐请方先生，完成独立 |\\n\\n#### 随身道具\\n- **团扇**（核心道具）：梅花绣纹，绣线已松，每次说完致命信息掩嘴笑\\n- **社交笔记**（暗线道具）：她能记住每个人的生辰、软肋和欲望\\n\\n---\\n\\n## 二、反派\\n\\n### 顾长渊（渣男世子）\\n\\n#### 基本信息\\n- **身份**：侯府世子（爵位继承人）\\n- **父亲**：老侯爷（仅侧面提及，第27章砸书房）\\n- **母亲**：侯夫人（仅侧面提及，第27章清理院子）\\n- **外表**：温润如玉，常穿月白色长衫\\n- **年龄**：约二十出头\\n\\n#### 性格特征\\n\\n**表面**：\\n- 温文尔雅，谦谦君子\\n- 谈吐风雅，举止得体\\n- 让人放下戒心的\\\"好人\\\"形象\\n\\n**内核**：\\n- 极度自负，看不起商贾出身的沈家\\n- 精于算计，商品是\\\"爱情\\\"\\n- 核心信念：\\\"女人嘛，好哄\\\"、\\\"女人终究是女人\\\"\\n- 贪婪且轻视女性——这是他致命的盲区\\n\\n#### 前世经历\\n- 利用沈家姐妹的资源和感情，平步青云登上户部高位\\n- 挑拨离间让两姐妹互斗至死\\n- 最终搂着丞相之女林婉兮，亲口承认利用\\n- \\\"我只是借你们沈家的钱袋子，铺我的青云路。\\\"\\n\\n#### 致命弱点\\n- 自负：至死不信女人能有翻天的智慧\\n- 贪婪：挪用公款、多线操作、越陷越深\\n- 轻视女性：即使\\\"诸事不顺\\\"，也不怀疑姐妹\\n- 真商人假君子：嘴上风雅，心里全是生意\\n\\n#### 罪行清单（实际内容统计）\\n| 罪行 | 金额/内容 | 证据 |\\n|------|---------|------|\\n| 盐铺账目造假 | 近2000两 | 账本中\\\"特定\\\"\\\"杂项\\\"条目 |\\n| 挪用户部公款 | 13000两 | 周书办被查获的私账 |\\n| 向沈家多次借款 | 7000+两 | 借据（沈清荷保管） |\\n| 虚假投资人协议 | 2000两 | 合伙契书（沈清荷保留） |\\n| 抬高盐铺采购价中饱私囊 | 数额不明 | 赵四提供的证据 |\\n\\n#### 人物弧线（权力下坠曲线）\\n\\n| 章节 | 状态 | 关键事件 |\\n|------|------|---------|\\n| 第1-3章 | 志得意满 | 两个女人为我争风吃醋，一切尽在掌握 |\\n| 第4-9章 | 隐隐不安 | 南货被截、传言四起，但归因于运气不好 |\\n| 第10章 | 信心巅峰 | 拿下漕运资格，以为大计将成 |\\n| 第13章 | 开始怀疑 | 派人调查，被姐妹完美伪装骗过 |\\n| 第16-17章 | 焦虑加深 | 盐铺收入下降、粮商催款 |\\n| 第18-19章 | 假装镇定 | 查账通过、投资到位，又放心了 |\\n| 第20章 | 恍然大悟 | 三个关键人物同时消失，但不敢信是沈清荷 |\\n| 第21-23章 | 疯狂补救 | 四处借钱被拒、周书办被抓、龙井茶出现在书房 |\\n| 第24章 | 真相大白 | 姐妹当面对质，揭露一切 |\\n| 第25章 | 彻底崩溃 | 公堂定罪、林婉兮冷眼、锒铛入狱 |\\n| 第26-27章 | 无力挣扎 | 反咬失败、削爵、发配北疆 |\\n| 第28章 | 彻底出局 | 婚约被撕毁、侯府试图挽回被拒 |\\n\\n#### 创作铁律\\n- ✅ 聪明但自负——他不是蠢，是看不起女人\\n- ✅ 在中期之前（第13-19章）察觉有\\\"幕后黑手\\\"但不信是姐妹\\n- ✅ 不洗白——没有\\\"深情无奈\\\"的戏码\\n- ✅ 结局：人财两空，身败名裂，发配边疆\\n\\n---\\n\\n## 三、核心盟友\\n\\n### 赵四（第一个内线）\\n\\n- **身份**：侯府盐铺二掌柜\\n- **年龄**：约三十岁\\n- **工龄**：为侯府工作六年\\n- **性格**：老实本分、不善交际、孝顺\\n- **家庭**：母亲常年咳疾，需要定期抓药；妹妹在绣坊做学徒\\n- **住址**：侯府西边巷子第三家，门口有棵槐树\\n- **被策反方式**：沈清莲亲自登门，承诺沈家铺子的职位、双倍月钱、让他照顾母亲\\n- **作用**：\\n  - 提供盐铺真实账目（揭露顾长渊抬高采购价中饱私囊）\\n  - 向顾长渊提供假情报（雪盐日产量只有200斤，实际500斤）\\n  - 成为姐妹在侯府内部的眼线\\n- **出场**：第8章（策反）、第16章（提供假情报）\\n\\n### 陈伯远（制盐伙伴）\\n\\n- **身份**：盐匠，手艺人\\n- **性格**：老实、技术好但不善经营\\n- **地点**：原作坊在城外东边五六里，后迁至城东运河边\\n- **技术**：只会做灰盐（低价）\\n- **被提升方式**：沈清荷带着\\\"豆浆法\\\"找上门——卤水中加豆浆去除杂质，产出纯白如雪的\\\"雪盐\\\"\\n- **合作关系**：沈清荷提供资金和销路，陈伯远提供技术，五五分账\\n- **发展轨迹**：\\n  - 第11章：小作坊，几口锅\\n  - 第14章：六口大锅，日产500斤\\n  - 第29章：八口锅→二十口锅，供应官盐\\n- **出场**：第11章、第14章、第29章\\n\\n### 刘德旺（粮商盟友）\\n\\n- **身份**：京城粮商\\n- **资历**：与侯府合作八年\\n- **性格**：稳重、话少、守信、讲义气\\n- **与渣男关系**：顾长渊欠他1800两粮款未还，早已不满\\n- **被策反方式**：沈清莲在赏春宴上主动接触，暗示沈家更可靠\\n- **策反条件**：沈家所有粮食业务过他的手，市价交易，不拖欠货款\\n- **额外作用**：成为姐妹监控渣男动向的暗线\\n- **出场**：第12章（初次接触）、第15章（正式入伙）\\n\\n### 方先生（书院教师）\\n\\n- **身份**：女性学者，曾在江南书院任教，退休回京\\n- **出场**：第29章（沈清莲三顾茅庐，第三次带自酿桂花酒才请动）\\n- **作用**：清莲书院第一位先生，象征沈清莲的事业独立\\n\\n---\\n\\n## 四、次要角色\\n\\n### 渣男阵营（被姐妹击败的一方）\\n\\n| 姓名 | 身份 | 与渣男关系 | 结局 |\\n|------|------|----------|------|\\n| 孙旺财 | 东市掮客 | 渣男找的中介 | 被沈清荷收买后消失（第20章） |\\n| 周书办 | 户部书办，二十年老吏 | 渣男贪污同谋 | 匿名信举报后被逮捕（第23章） |\\n| 吴管事 | 侯府管家 | 替渣男跑腿调查 | 调查无果 |\\n| 钱管事 | 侯府账房，十年老仆 | 忠于侯府 | 给渣男最后500两私房钱（第21章） |\\n| 王夫人 | 王御史之妻 | 社交圈信息来源 | 被沈清莲利用传播谣言 |\\n| 张侍郎太太 | 吏部张侍郎之妻 | 社交圈信息来源 | 同上 |\\n| 周三小姐 | 周家小姐 | 社交圈信息来源 | 同上 |\\n| 吴老板 | 渣男远亲，西城丝绸商 | 曾受侯府两千两救命钱 | 拒绝借钱（第21章） |\\n| 林老板 | 渣男前生意伙伴 | 曾被渣男帮过拿下河道工程 | 拒绝借钱：\\\"你拿什么还\\\"（第21章） |\\n| 陈员外郎 | 户部官员 | 收过渣男礼 | 拒绝帮忙拖延调查（第22章） |\\n\\n### 中立/背景角色\\n\\n| 姓名 | 身份 | 作用 |\\n|------|------|------|\\n| 周老板 | 金陵周记商行 | 渣男想买他的南货，被沈清荷截胡（第4章） |\\n| 马老板 | 漕运批文持有者 | 卖了一个批文（沈清荷通过中间人买下） |\\n| 王掌柜 | 城南王家杂货铺 | 雪盐第一个零售点（第14章） |\\n| 王主事 | 户部主事 | 渣男想贿赂的对象之一 |\\n| 户部侍郎 | 户部二把手 | 收到匿名信、主持审判（第23、25章） |\\n| 老侯爷 | 顾长渊之父 | 仅侧面提及，儿子事发后砸书房（第27章） |\\n| 侯夫人 | 顾长渊之母 | 仅侧面提及，清理儿子院落（第27章） |\\n| 刘管事 | 侯府管家，二十年老仆 | 替老侯爷送信试图挽回婚约（第28章） |\\n| 李夫人 | 西城李府主人 | 第7章赏花宴主办者 |\\n| 周侍郎 | 吏部官员 | 第2章被沈清莲提及有私生子 |\\n\\n---\\n\\n## 五、角色关系图谱\\n\\n```\\n                    前世记忆（共同仇人）\\n                         ↓\\n    ┌──────────────────────────────────────┐\\n    │                                      │\\n┌───────┐  姐妹同盟（坚不可摧）  ┌───────┐\\n│沈清荷  │ ←────────────────→  │沈清莲  │\\n│商道之刃 │   算账 / 算人       │人心之网 │\\n└───┬───┘                      └───┬───┘\\n    │                              │\\n    │ 截胡生意                     │ 策反拉拢\\n    │ 改良制盐                     │ 散布谣言\\n    │ 设陷阱                       │ 安插内线\\n    │                              │\\n    ▼                              ▼\\n┌─────────────────────────────────────────┐\\n│              顾长渊（渣男）              │\\n│         侯府世子/月白长衫/温润如玉        │\\n│           致命弱点：轻视女性              │\\n│                                          │\\n│  ←── 经济封锁（截胡/架空/造假）         │\\n│  ←── 社交孤立（策反/谣言/内线）         │\\n│  ←── 法律打击（匿名信/借据/账本证据）    │\\n└─────────────────────────────────────────┘\\n    │\\n    │ 被击败后\\n    ▼\\n  削爵 + 发配北疆 + 终身不得回京\\n```\\n\\n### 姐妹分工矩阵\\n\\n| 维度 | 沈清荷 | 沈清莲 |\\n|------|--------|--------|\\n| 核心武器 | 算盘（算账） | 团扇（算人） |\\n| 战场 | 商场 | 社交场 |\\n| 攻击方式 | 截胡/架空/垄断 | 策反/谣言/收买 |\\n| 关键盟友 | 陈伯远、周老板 | 赵四、刘德旺、方先生 |\\n| 金句 | \\\"这笔账，划不来\\\" | \\\"哎呀，这可不巧了么\\\" |\\n| 终局成就 | 皇商掌权人 | 女子书院创办人 |\\n\\n### 情感纽带\\n- **姐妹情**：通过动作细节表达——夹菜、对视、挡在身前、共饮酒\\n- **对渣男**：零情感，纯工具，每一句甜言蜜语都是台词\\n- **对盟友**：以利相交，同时给予尊重——不是施舍，是合作\\n\\n---\\n\\n## 六、角色一致性检查清单\\n\\n### 沈清荷\\n- [x] 是否每次愤怒都在账本上记一笔而非吼叫？\\n- [x] 是否重大决定前都拨动了算盘？\\n- [x] 是否用数字和账本说话而非情绪？\\n- [x] 是否对妹妹绝对信任？\\n\\n### 沈清莲\\n- [x] 是否每次说到致命信息都用团扇掩笑？\\n- [x] 是否对外人笑里藏刀，对姐姐笑里真诚？\\n- [x] 是否发挥了\\\"记住每个人的软肋\\\"的能力？\\n- [x] 是否对渣男零真情？\\n\\n### 顾长渊\\n- [x] 是否始终轻视女性？\\n- [x] 是否第20章前都没怀疑姐妹？\\n- [x] 是否没被洗白？\\n- [x] 是否结局符合\\\"人财两空、身败名裂\\\"？\\n\\n*创建时间：2026-06-16*\\n*基于：宪法v2.0.0 + 规格书v1.3.0 + 创作计划v1.0.0 + 30章实际内容*\", \"production_brief\": \"项目类型：\\n\\n- 古装女性权谋短剧\\n- 重生\\n- 宅斗\\n- 家族利益博弈\\n- 商道权谋\\n- 人物之间的试探、隐忍、算计与反击\\n\\n类型边界：\\n\\n- “权谋”表示人物关系、利益冲突和叙事节奏。\\n- 如原文不存在皇宫、后宫、妃嫔、皇帝或朝廷线，不得擅自增加。\\n- 不得为了制造“宫斗感”改变原文世界观和人物身份。\\n\\n改编方向：\\n\\n- 真人短剧叙事\\n- 冲突清晰\\n- 节奏紧凑\\n- 情绪递进明确\\n- 保留人物核心动机\\n- 内心描写优先转化为动作、微表情、停顿、呼吸和视线变化\\n- 不得为了追求爽感篡改原文事实\\n- 不得确认 unknown_do_not_invent 内容\\n\\n视觉方向：\\n\\n- 真人写实风格\\n- 古装影视剧质感\\n- 真实人物皮肤纹理\\n- 真实服饰和织物纹理\\n- 低饱和、柔和电影布光\\n- 精致但不过度仙侠化\\n- 非动漫\\n- 非二次元\\n- 非游戏建模\\n- 场景、服饰和道具符合人物身份及故事环境\\n\\n生产约束：\\n\\n- 主要画幅为 16:9\\n- 后续 LibTV 视频 Unit 必须为 5–15 秒\\n- 人物脸部与骨相保持一致\\n- 服装、发型、配饰保持连续\\n- 场景布局和家具位置保持一致\\n- 人物站位、左右关系和视线保持一致\\n- 光源方向和时间状态保持一致\\n- 前后视频节点动作必须连续\", \"series_canon\": \"# 世界观设定\\n\\n## 元数据\\n- **作品**：商海沉浮·釜底抽薪篇\\n- **宪法版本**：v2.0.0\\n- **创建日期**：2026-06-16\\n- **世界观基调**：偏架空爽文（商业逻辑为主，朝堂为背景板）\\n- **来源**：规格书澄清#1 + 30章实际内容\\n\\n---\\n\\n## 一、时代背景\\n\\n### 王朝设定\\n- **国号**：未命名（架空王朝，不深究历史朝代）\\n- **政治结构**：君主制 + 六部制（仿古，不考据具体年代）\\n- **核心设定**：商业发达，盐铁等重要物资半官营半私营\\n- **特点**：爵位世袭、科举入仕并存；官商合作普遍\\n\\n### 创作原则\\n- 朝堂只是背景板——政治斗争不展开，焦点始终在商战\\n- 法律、官职、商业规则服务于故事，不追求历史考据\\n- 架空自由度——可以自创商业规则，不需对应真实朝代\\n\\n---\\n\\n## 二、政治体系\\n\\n### 爵位层级（简化版）\\n\\n| 爵位 | 说明 | 故事中对应 |\\n|------|------|----------|\\n| 侯府 | 中高层贵族，世袭罔替 | 顾长渊家族 |\\n| 丞相府 | 文官之首 | 林婉兮之父（外任中） |\\n\\n**爵位继承**：\\n- 世子是法定继承人\\n- 犯罪可被削去世子爵位（顾长渊的结局）\\n- 老侯爷在世时，侯府仍由他名义上掌管\\n\\n### 朝廷六部（简化版）\\n\\n| 部门 | 职能 | 故事中涉及 |\\n|------|------|----------|\\n| 户部 | 财政、漕运、盐铁、税收 | 核心舞台 |\\n| 吏部 | 官员任免 | 间接涉及（张侍郎） |\\n| 工部 | 工程、河道 | 间接涉及（林老板的河道工程） |\\n\\n### 户部官僚层级（故事实际出现）\\n\\n| 职位 | 品级 | 职能 | 代表人物 |\\n|------|------|------|---------|\\n| 户部侍郎 | 三品 | 户部二把手，主持审判 | 审判顾长渊 |\\n| 户部郎中 | 五品 | 司局长官 | 顾长渊的目标职位 |\\n| 户部主事 | 六品 | 处级官员 | 王主事 |\\n| 户部员外郎 | 从五品 | 司局副职 | 陈员外郎 |\\n| 户部书办 | 不入流 | 管账的文书吏 | 周书办（二十年老吏） |\\n\\n**官职体系说明**：\\n- 郎中是实权职位，管一司事务\\n- 书办虽无品级，但掌握账目命脉，实际权力不小\\n- 进入六部需要\\\"运作\\\"——送礼、攀关系、找引荐人\\n\\n---\\n\\n## 三、商业体系\\n\\n### 货币政策\\n\\n| 单位 | 说明 | 实际购买力参考 |\\n|------|------|-------------|\\n| 文 | 铜钱，最小单位 | 1斤灰盐=15文；1斤雪盐=40文 |\\n| 两（银子） | 银两，基本交易单位 | 1两≈1000文；一个人月钱约3-5两 |\\n| 银票 | 钱庄发行的纸币 | 大额交易用，京城最大钱庄最可信 |\\n\\n**购买力锚定**：\\n- 一个盐铺二掌柜月钱：数两银子\\n- 漕运批文转让价：1800两\\n- 渣男挪用户部公款总额：13000两（足以发配三千里）\\n- 侯府中人二十年积蓄：500两\\n\\n### 钱庄制度\\n- 京城有主要钱庄若干，最大的那家信誉最高\\n- 银票可跨城兑现\\n- 钱庄也做借贷（有利息，连本带利）\\n- 借据（借据）具有法律效力\\n\\n### 盐业体系\\n\\n#### 盐的种类与等级\\n\\n| 品种 | 品质 | 价格 | 说明 |\\n|------|------|------|------|\\n| 灰盐 | 低 | 15文/斤 | 普通百姓用盐，颜色灰暗 |\\n| 青盐 | 中 | 30文/斤 | 好盐，市面主流 |\\n| 雪盐 | 高 | 40文/斤 | 沈清荷的技术创新，纯白如雪 |\\n\\n#### 制盐技术（实际设定）\\n- **传统工艺**：卤水熬煮，产出灰盐或青盐\\n- **豆浆法（核心创新）**：在卤水中加豆浆，杂质随豆浆沫浮出，撇去后得到纯白结晶\\n- **来源**：南方一本杂记中记载的民间偏方（沈清荷前世记忆）\\n- **技术壁垒**：简单但没人知道——信息差就是商业优势\\n\\n#### 盐铁渠道（权力结构）\\n- 盐作为必需品商品，由政府控制流通\\n- 贵族和官员可以通过\\\"关系\\\"获得盐的经营权\\n- 侯府掌握盐铺——这是一种权力资源\\n- 变相垄断：有权有势者垄断最好的渠道\\n\\n#### 盐引制度\\n- 盐引是政府颁发的食盐经营许可证\\n- 持有盐引者可合法经营食盐\\n- 皇商资格是最高级别的盐引\\n\\n### 漕运体系\\n\\n#### 漕运（运河运输系统）\\n- 政府控制的粮食物资运输网络\\n- 核心路线：江淮→京城（运河沿线）\\n\\n#### 供应商准入\\n- 需要\\\"供应商资格\\\"（批文），有限额——\\\"一个萝卜一个坑\\\"\\n- 获得方式：购买、继承、或者通过关系运作\\n- 转让价格：1800两左右（故事中马老板卖批文的价格）\\n\\n#### 运营成本\\n- 租船费 + 雇船工 + 码头仓库租赁 + 沿途关卡过路费\\n- 一条批文年收入可达上万两\\n- 但前期投入大，现金流压力重\\n\\n#### 盈利模式\\n- 政府支付固定运费\\n- 同时可夹带部分私货（灰色地带）\\n- 关键在于压低运营成本\\n\\n### 其他主要产业\\n\\n| 产业 | 经营模式 | 故事中涉及 |\\n|------|---------|----------|\\n| 南货（金陵） | 丝绸、茶叶、干货 | 第4章截胡的第一单 |\\n| 粮食 | 城中有多家粮商 | 刘德旺的粮铺 |\\n| 木材 | 河道工程 | 渣男帮林老板拿河道工程 |\\n| 丝绸 | 西城多家铺子 | 吴老板是侯府远亲 |\\n| 杂货 | 油盐酱醋 | 王掌柜的王家杂货铺 |\\n\\n### 商业规则\\n\\n#### 账目制度\\n- 店铺必须记流水账（流水账）\\n- 账目分类：进项（收入）、支出、\\\"特定\\\"（指定用途）、\\\"杂项\\\"、\\\"人情往来\\\"、\\\"采买\\\"、\\\"其他\\\"\\n- \\\"特定\\\"和\\\"杂项\\\"是常见的造假科目（顾长渊即在此做手脚）\\n- 账册可作为法律证据\\n\\n#### 合伙方式\\n- 五五分账（最常见）\\n- 干股（不出钱只出人/技术，按约定比例分利润）\\n- 合伙契书：写明投入、分成、退出条件\\n- 沈清荷的合伙人模式：她出资金和销路，陈伯远出技术，五五分\\n\\n#### 统一定价策略\\n- 沈清荷的雪盐统一零售价40文/斤\\n- 避免各铺子恶性竞价\\n- 树立品牌形象：雪盐=好盐=贵得有道理\\n\\n#### 中介（掮客）体系\\n- 东市等地有专门的中介人\\n- 撮合买卖双方，收取佣金\\n- 孙旺财是典型的中介：人脉广但不专，谁给钱帮谁\\n\\n---\\n\\n## 四、社会结构\\n\\n### 阶层\\n| 阶层 | 代表 | 特征 |\\n|------|------|------|\\n| 贵族 | 侯府、丞相府 | 世袭爵位，有特权 |\\n| 官员 | 户部侍郎、书办 | 有实权但非世袭 |\\n| 商人 | 沈家、刘德旺 | 有钱但地位低 |\\n| 手艺人 | 陈伯远 | 凭手艺吃饭 |\\n| 平民 | 赵四一家 | 工薪阶层 |\\n\\n### 商人的社会地位\\n- 重农抑商的传统仍在，商人有钱但没地位\\n- 商人通过与贵族联姻来\\\"洗白\\\"身份——顾长渊与沈清荷的婚约本质是侯府拿爵位换沈家财富\\n- 皇商资格算是商人的最高荣誉（沈清荷第29章获得）\\n\\n### 女性的社会处境\\n- 未出阁的姑娘主要职责：嫁人\\n- 管理家族生意是例外（因沈家父母不在/无能，姐妹当家）\\n- 女子书院是突破性的新事物（沈清莲第29章创办）\\n- 清莲书院的核心理念：\\\"读书不是为了嫁人。是为了让你们以后——有的选。\\\"\\n\\n---\\n\\n## 五、婚约与法律\\n\\n### 婚约制度\\n- 议亲（谈婚论嫁）→ 定亲 → 婚约成立\\n- 婚书是正式文书，红纸黑字，盖双方家族印章\\n- 毁约需要正当理由（如一方犯罪被削爵——沈清荷以此为由撕毁婚书）\\n\\n### 司法制度（简化）\\n\\n**举报途径**：\\n- 匿名信可以触发调查（沈清荷向户部侍郎送匿名信）\\n- 附带证据的举报更有分量\\n- 门房接收信件后层层传递\\n\\n**审判程序**：\\n- 户部大堂审理（第25章）\\n- 原告方出示证据\\n- 被告方认罪或辩护\\n- 数罪并罚\\n\\n**刑罚体系**：\\n| 罪行 | 惩罚 |\\n|------|------|\\n| 挪用户部公款 | 革职 + 发配充军 |\\n| 伪造账目 | 计入从重情节 |\\n| 贪墨铺银 | 削去爵位 |\\n| 贪污万两以上 | 发配三千里，终身不得回京 |\\n| 数罪并罚 | 叠加处罚 |\\n\\n---\\n\\n## 六、地理环境\\n\\n### 京城及周边\\n\\n```\\n                        北疆（流放地）\\n                           ↕ 数千里\\n                        京城（核心舞台）\\n                       ↙  ↓  ↘\\n               西城区   皇城区   东城区\\n              (李府等)  (户部等)  (东市/码头/\\n                                   运河/书院)\\n                           ↓\\n                        江淮地区\\n                        (运河沿线)\\n                           ↓\\n                        金陵（南京）\\n                   （南货集散地，两天路程）\\n                           ↓\\n                        江南\\n                  （沈家庄园、方先生故地）\\n```\\n\\n### 主要地点汇总\\n\\n#### 沈家\\n- 书房（沈清荷的核心场景）：窗户对着桂花树，有暗格藏漕运批文\\n- 后院亭子：姐妹饮酒、会客、最终场景\\n- 海棠树：婚约灰烬最终撒落之处\\n- 厅堂：接待客人、烧毁婚书\\n\\n#### 侯府\\n- 书房（顾长渊的核心场景）\\n- 盐铺（最大的那家）：赵四在此工作\\n- 侧门/巷子：渣男的秘密出入通道\\n\\n#### 商业区\\n- 东市：掮客活跃、王家杂货铺所在地\\n- 码头：城东运河边，漕运装卸处\\n- 城东运河边：陈伯远扩建后的新作坊\\n\\n#### 官署\\n- 户部大堂：审判场所\\n- 户部侧厢房：周书办工作处\\n- 户部门房值班室：匿名信送达处\\n\\n#### 社交场所\\n- 城西李府：赏花宴\\n- 张侍郎府：赏春宴\\n- 锦绣阁（东城丝绸铺）：沈清莲与王夫人的偶遇地点\\n\\n#### 女性事业空间\\n- 清莲书院（东城）：前退休官员旧宅，院里有槐树\\n- 陈伯远盐坊（城外→运河边）：从小作坊到大工场\\n\\n---\\n\\n## 七、文化习俗\\n\\n### 社交礼仪\\n- 初次见面递\\\"帖子\\\"（名帖）\\n- 做客带礼物（绸料等）\\n- 社交场合：赏花宴、赏春宴是核心社交场景\\n- 贵妇圈是信息流通渠道——沈清莲的主要战场\\n\\n### 送礼文化\\n- 桂花糕（天香楼）：男女之间送，有暧昧意味\\n- 龙井茶（上等）：顾长渊案发时出现在书房，是姐妹的暗示\\n- 桂花酒（自酿）：沈清莲三顾茅庐请方先生的诚意\\n- 绸料：社交场合的标准伴手礼\\n\\n### 时间标记\\n- 故事时间跨度：约一年（春天→次年春/夏）\\n- 月份：正月、三月、四月、五月、六月均有出现\\n- 花卉轮回：桂花打苞→满开→花落；海棠花开花谢；牡丹盛开\\n\\n---\\n\\n## 八、经济世界观核心规则\\n\\n### 1. 信息差即为权力\\n- 沈清荷利用前世记忆知道漕运批文要转手\\n- 沈清莲知道每个人的软肋和秘密\\n- \\\"豆浆法\\\"在书中就有，但别人不知道\\n- 姐妹的复仇本质：用信息差碾压权力差\\n\\n### 2. 账目即为武器\\n- 每一笔账都是证据\\n- 沈清荷的账本记录了渣男全部罪行\\n- \\\"特定\\\"、\\\"杂项\\\"是贪污的入口\\n- 账目可以在公堂上作为呈堂证供\\n\\n### 3. 渠道即为命脉\\n- 控制渠道等于控制市场\\n- 盐铁渠道被侯府垄断 → 沈清荷开辟雪盐渠道 → 架空侯府\\n- 漕运渠道是渣男的大计划 → 姐妹从中设陷阱\\n- 粮食渠道被策反 → 渣男断供\\n\\n### 4. 人情即为资本\\n- 沈清莲的核心竞争力\\n- 记住每个人的软肋和欲望 → 精准策反\\n- 真诚对待赵四、刘德旺 → 建立非交易性信任\\n- 债主对渣男不好 ≠ 盟友对姐妹好，关键在\\\"怎么对待人\\\"\\n\\n---\\n\\n## 九、写作约束\\n\\n### 世界观的\\\"留白\\\"策略\\n- 不交代王朝的具体国号、帝号——因为不重要\\n- 不细说六部运作的细节——需要什么设定什么\\n- 不展开朝堂政治——始终以商业博弈为主\\n- 不加入魔法/修仙/系统——纯现实商战（虽然架空）\\n\\n### 架空爽文的自由度\\n- 可以自创商业规则、法律条文、官职体系\\n- 不需要严格考据历史——因为本来就不是历史小说\\n- 逻辑自洽 > 历史真实\\n- 爽感优先——但要在逻辑合理的范围内\\n\\n---\\n\\n*创建时间：2026-06-16*\\n*基于：规格书v1.3.0 + 创作计划v1.0.0 + 30章实际内容*\\n*宪法合规：偏架空爽文（澄清#1），朝堂为背景板*\", \"source_run_id\": \"b360d68e225c4e6da68f491d5d044024\", \"source_script_approval_record\": {\"action\": \"script_approved\", \"artifact_id\": \"shengsi-chapter-001\", \"created_at\": \"2026-06-28T12:48:03.895524Z\", \"note\": \"\", \"record_id\": \"191fd857c39147108ace296578e3bc7b\", \"reviewer\": \"verifier\", \"revision_id\": \"c37329ee465c464b99bc5a57b690983f\", \"sequence\": 1}, \"source_script_approval_record_id\": \"191fd857c39147108ace296578e3bc7b\", \"source_script_artifact_id\": \"shengsi-chapter-001\", \"source_script_content_hash\": \"ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a\", \"source_script_markdown\": \"# Mock Drama Script Revision\\n\\nruntime_model: mock-script\\nsource_basis: manifest\\n\\n## Scene: 1-1\\n\\n【画面】\\n女主在清晨醒来，意识到命运重启。\\n\\n【动作】\\n她检查身边物件，确认眼前不是幻觉。\\n\\n【台词】\\n女主：这一世，我要先看清局。\\n\\n## Scene: 1-2\\n\\n【画面】\\n账册摊开，旧日线索重新浮现。\\n\\n【动作】\\n她整理证据，把危险关系和家族账目分开标记。\\n\\n【台词】\\n女主：账不会骗人，人心才会。\\n\", \"source_script_revision_id\": \"c37329ee465c464b99bc5a57b690983f\"}, \"output_contract\": {\"format\": \"markdown\", \"parser_version\": \"storyboard-markdown-v1\", \"profile\": \"storyboard-markdown-mvp-v1\", \"supported_artifacts\": [\"storyboard_markdown\"], \"unsupported_bundle_artifacts\": [\"storyboard_json_bundle\", \"shot_prompt_package\", \"visual_asset_binding_package\", \"libtv_execution_package\", \"agnes_execution_package\"]}, \"request_format_version\": \"runtime-request-v1\", \"runtime_config\": {\"model\": \"mock-storyboard\", \"provider\": \"mock\", \"timeout_seconds\": 60}, \"skill\": {\"execution_profile\": \"storyboard-markdown-mvp-v1\", \"package_hash\": \"347b27cfeb0b08c7d1acf825daacd6723f194d933ed34c0bdd18d821f3478230\", \"skill_id\": \"ai-drama-storyboard-design-skill\", \"version\": \"v0.1.0\"}, \"skill_instruction\": {\"content\": \"# AI Drama Storyboard Design Skill v0.1.0\\n\\n## Purpose\\n\\nConvert an approved drama script revision into a creator-facing storyboard revision with shot-level continuity, source coverage, and approval traceability.\\n\\n## Scope\\n\\nUse only for storyboard design. Do not emit shot prompts, LibTV packages, visual asset plans, image/video prompts, or execution commands.\\n\\n## Required Inputs\\n\\n- approved script revision\\n- source approval record\\n- `series_canon`\\n- `characters`\\n- `production_brief`\\n\\n## Markdown Contract\\n\\n- Top header: `# Storyboard`\\n- Scene header: `## 场次：{scene_id}`\\n- Shot header: `### 镜头 {shot_order}`\\n- Every shot must include:\\n  - `scene_id`\\n  - `shot_id`\\n  - `shot_order`\\n  - `source_scene_reference`\\n  - `duration_seconds`\\n  - `shot_size`\\n  - `camera_angle`\\n  - `camera_movement`\\n  - `visual_composition`\\n  - `character_positions`\\n  - `character_actions`\\n  - `emotion_performance`\\n  - `dialogue`\\n  - `sound_notes`\\n  - `continuity_in`\\n  - `continuity_out`\\n\\n## Rules\\n\\n- Preserve source scene order and source facts.\\n- Do not add new core plot events.\\n- Every shot duration must be 5-15 seconds.\\n- Every scene shot must bind a stable `source_scene_reference`.\\n- `shot_id` must be stable within the chapter and unique per shot.\\n- `shot_order` must be unique and strictly increasing within each scene.\\n- `continuity_in` and `continuity_out` must describe the immediate transition state.\\n- `character_positions`, `character_actions`, and `emotion_performance` must be explicit for every shot.\\n- Do not mention downstream execution artifacts or terms.\\n\\n## Output\\n\\nWrite creator-facing Markdown storyboard only.\\n\", \"relative_path\": \"SKILL.md\", \"sha256\": \"9eeb47b0494816df974cf44f4b535b89600387e1160041cbe97a4af71537df2b\"}, \"system_instruction\": \"Follow the skill package and return only the requested Markdown Storyboard revision.\"}"
  },
  {
    "test_item": "Gate Persistence",
    "status": "PASS",
    "evidence": "{\"approval_record\": {\"action\": \"storyboard_approved\", \"artifact_id\": \"shengsi-chapter-001:storyboard\", \"created_at\": \"2026-06-28T12:48:04.033578Z\", \"note\": \"\", \"record_id\": \"1dd2a4d0b8ce49cd82493a1e01c95157\", \"reviewer\": \"verifier\", \"revision_id\": \"ef108da52ae9408dbd58ebbb7b9f67b8\", \"sequence\": 2}, \"artifact_id\": \"shengsi-chapter-001:storyboard\", \"content_hash\": \"e08a5f1a084858662578029458b2b036217c814b678be264f57340a29a6b78f8\", \"export_time\": \"2026-06-28T12:48:04.034816Z\", \"freshness_status\": \"FRESH\", \"input_references\": [{\"logical_type\": \"characters\", \"relative_path\": \"characters.md\", \"sha256\": \"1df41598fa2a0786c90539979c076cce950325ffed0e8e2c27de37657b6839fc\"}, {\"logical_type\": \"production_brief\", \"relative_path\": \"production-brief.md\", \"sha256\": \"8cbb61658176274e05681bac6769fabba5c8dd1eee14c0600db4b1a5dbc74f0d\"}, {\"logical_type\": \"series_canon\", \"relative_path\": \"series-canon.md\", \"sha256\": \"39da5039ea9aa3ff2fcc020278ad07db29d5eec3c042595171f26f08d98f138b\"}, {\"logical_type\": \"source_revision\", \"relative_path\": \"c37329ee465c464b99bc5a57b690983f\", \"sha256\": \"ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a\"}, {\"logical_type\": \"source_script_approval\", \"relative_path\": \"c37329ee465c464b99bc5a57b690983f\", \"sha256\": \"3dd9dd7ea205cfcb7dbb4d0b289e9a33f0fa88e55d1f710935d3d3a00059ba04\"}], \"model\": \"mock-storyboard\", \"package_hash\": \"347b27cfeb0b08c7d1acf825daacd6723f194d933ed34c0bdd18d821f3478230\", \"provider\": \"mock\", \"request_hash\": \"090b8000962d926f21fa73296cfda66497b487f5095127de3b35edce8382783c\", \"revision_id\": \"ef108da52ae9408dbd58ebbb7b9f67b8\", \"run_id\": \"4f9fd9dca391441a8d8f812dcd3bef52\", \"skill_id\": \"ai-drama-storyboard-design-skill\", \"skill_version\": \"v0.1.0\", \"source_approval_record\": {\"action\": \"script_approved\", \"artifact_id\": \"shengsi-chapter-001\", \"created_at\": \"2026-06-28T12:48:03.895524Z\", \"note\": \"\", \"record_id\": \"191fd857c39147108ace296578e3bc7b\", \"reviewer\": \"verifier\", \"revision_id\": \"c37329ee465c464b99bc5a57b690983f\", \"sequence\": 1}, \"source_revision_id\": \"c37329ee465c464b99bc5a57b690983f\", \"source_script_approval_record_id\": \"191fd857c39147108ace296578e3bc7b\", \"source_script_artifact_id\": \"shengsi-chapter-001\", \"source_script_content_hash\": \"ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a\", \"source_script_revision_id\": \"c37329ee465c464b99bc5a57b690983f\"}"
  },
  {
    "test_item": "Storyboard Run",
    "status": "PASS",
    "evidence": "4f9fd9dca391441a8d8f812dcd3bef52"
  },
  {
    "test_item": "Required Validators Execute",
    "status": "PASS",
    "evidence": "{\"storyboard_structure\": \"PASS\", \"storyboard_duration\": \"PASS\", \"storyboard_source_coverage\": \"PASS\", \"storyboard_continuity\": \"PASS\", \"genericity\": \"NOT_APPLICABLE\"}"
  },
  {
    "test_item": "Required N/A Block",
    "status": "PASS",
    "evidence": "{\"run_status\": \"VALIDATION_FAILED\", \"approval_blocked\": true, \"validator_status\": \"NOT_APPLICABLE\", \"validator_required\": true, \"validator_stderr\": \"requires complete bundle\\n\"}"
  },
  {
    "test_item": "Real Source Coverage",
    "status": "PASS",
    "evidence": "{\"SOURCE_SCRIPT_SCENES\": [\"1-1\", \"1-2\", \"1-3\"], \"STORYBOARD_SOURCE_REFERENCES\": [\"1-1\", \"1-1\", \"1-2\", \"1-2\"], \"MISSING_SOURCE_SCENES\": [\"1-3\"], \"EXTRA_SOURCE_REFERENCES\": [], \"ORDER_MISMATCH\": true}"
  },
  {
    "test_item": "Structure Fault Injection",
    "status": "PASS",
    "evidence": "validator tests cover malformed scene/shot layouts"
  },
  {
    "test_item": "Duration Fault Injection",
    "status": "PASS",
    "evidence": "validator tests cover duration bounds"
  },
  {
    "test_item": "Continuity Fault Injection",
    "status": "PASS",
    "evidence": "validator tests cover missing continuity fields"
  },
  {
    "test_item": "Approval Actions",
    "status": "PASS",
    "evidence": "storyboard_approved"
  },
  {
    "test_item": "Captured Provenance",
    "status": "PASS",
    "evidence": {
      "action": "script_approved",
      "artifact_id": "shengsi-chapter-001",
      "created_at": "2026-06-28T12:48:03.895524Z",
      "note": "",
      "record_id": "191fd857c39147108ace296578e3bc7b",
      "reviewer": "verifier",
      "revision_id": "c37329ee465c464b99bc5a57b690983f",
      "sequence": 1
    }
  },
  {
    "test_item": "Export Sidecar",
    "status": "PASS",
    "evidence": "{\"approval_record\": {\"action\": \"storyboard_approved\", \"artifact_id\": \"shengsi-chapter-001:storyboard\", \"created_at\": \"2026-06-28T12:48:04.033578Z\", \"note\": \"\", \"record_id\": \"1dd2a4d0b8ce49cd82493a1e01c95157\", \"reviewer\": \"verifier\", \"revision_id\": \"ef108da52ae9408dbd58ebbb7b9f67b8\", \"sequence\": 2}, \"artifact_id\": \"shengsi-chapter-001:storyboard\", \"content_hash\": \"e08a5f1a084858662578029458b2b036217c814b678be264f57340a29a6b78f8\", \"export_time\": \"2026-06-28T12:48:04.034816Z\", \"freshness_status\": \"FRESH\", \"input_references\": [{\"logical_type\": \"characters\", \"relative_path\": \"characters.md\", \"sha256\": \"1df41598fa2a0786c90539979c076cce950325ffed0e8e2c27de37657b6839fc\"}, {\"logical_type\": \"production_brief\", \"relative_path\": \"production-brief.md\", \"sha256\": \"8cbb61658176274e05681bac6769fabba5c8dd1eee14c0600db4b1a5dbc74f0d\"}, {\"logical_type\": \"series_canon\", \"relative_path\": \"series-canon.md\", \"sha256\": \"39da5039ea9aa3ff2fcc020278ad07db29d5eec3c042595171f26f08d98f138b\"}, {\"logical_type\": \"source_revision\", \"relative_path\": \"c37329ee465c464b99bc5a57b690983f\", \"sha256\": \"ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a\"}, {\"logical_type\": \"source_script_approval\", \"relative_path\": \"c37329ee465c464b99bc5a57b690983f\", \"sha256\": \"3dd9dd7ea205cfcb7dbb4d0b289e9a33f0fa88e55d1f710935d3d3a00059ba04\"}], \"model\": \"mock-storyboard\", \"package_hash\": \"347b27cfeb0b08c7d1acf825daacd6723f194d933ed34c0bdd18d821f3478230\", \"provider\": \"mock\", \"request_hash\": \"090b8000962d926f21fa73296cfda66497b487f5095127de3b35edce8382783c\", \"revision_id\": \"ef108da52ae9408dbd58ebbb7b9f67b8\", \"run_id\": \"4f9fd9dca391441a8d8f812dcd3bef52\", \"skill_id\": \"ai-drama-storyboard-design-skill\", \"skill_version\": \"v0.1.0\", \"source_approval_record\": {\"action\": \"script_approved\", \"artifact_id\": \"shengsi-chapter-001\", \"created_at\": \"2026-06-28T12:48:03.895524Z\", \"note\": \"\", \"record_id\": \"191fd857c39147108ace296578e3bc7b\", \"reviewer\": \"verifier\", \"revision_id\": \"c37329ee465c464b99bc5a57b690983f\", \"sequence\": 1}, \"source_revision_id\": \"c37329ee465c464b99bc5a57b690983f\", \"source_script_approval_record_id\": \"191fd857c39147108ace296578e3bc7b\", \"source_script_artifact_id\": \"shengsi-chapter-001\", \"source_script_content_hash\": \"ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a\", \"source_script_revision_id\": \"c37329ee465c464b99bc5a57b690983f\"}"
  },
  {
    "test_item": "Staleness",
    "status": "PASS",
    "evidence": "{\"script_a_revision_id\": \"bf2ebcbf8d504f29b2ad98d8f9e38538\", \"script_b_revision_id\": \"f40d6acb26b7401b9b85c5f75993e66d\", \"storyboard_a1_revision_id\": \"17db560768204078915247b0770a7be1\", \"storyboard_a1_freshness_after_b\": \"STALE\", \"storyboard_a1_source_revision_id\": \"bf2ebcbf8d504f29b2ad98d8f9e38538\", \"storyboard_a1_source_approval_record\": {\"sequence\": 1, \"record_id\": \"422eb97edf77446793be11ba30625858\", \"revision_id\": \"bf2ebcbf8d504f29b2ad98d8f9e38538\", \"artifact_id\": \"shengsi-chapter-001\", \"action\": \"script_approved\", \"reviewer\": \"verifier\", \"note\": \"\", \"created_at\": \"2026-06-28T12:48:04.100506Z\"}}"
  },
  {
    "test_item": "Compare",
    "status": "PASS",
    "evidence": "{\"script_a_revision_id\": \"bf2ebcbf8d504f29b2ad98d8f9e38538\", \"script_b_revision_id\": \"f40d6acb26b7401b9b85c5f75993e66d\", \"storyboard_a1_revision_id\": \"17db560768204078915247b0770a7be1\", \"storyboard_a1_freshness_after_b\": \"STALE\", \"storyboard_a1_source_revision_id\": \"bf2ebcbf8d504f29b2ad98d8f9e38538\", \"storyboard_a1_source_approval_record\": {\"sequence\": 1, \"record_id\": \"422eb97edf77446793be11ba30625858\", \"revision_id\": \"bf2ebcbf8d504f29b2ad98d8f9e38538\", \"artifact_id\": \"shengsi-chapter-001\", \"action\": \"script_approved\", \"reviewer\": \"verifier\", \"note\": \"\", \"created_at\": \"2026-06-28T12:48:04.100506Z\"}}"
  },
  {
    "test_item": "DB Upgrade",
    "status": "PASS",
    "evidence": "fresh sqlite schema initialized in temp db"
  },
  {
    "test_item": "Restart Safety",
    "status": "PASS",
    "evidence": "temp db reopened successfully"
  },
  {
    "test_item": "Runtime Request Deduplication",
    "status": "PASS",
    "evidence": "{\"context_files\": [{\"content\": \"# AI Drama Storyboard Design Skill\\n\\nFormal storyboard design package for approved drama script revisions.\\n\", \"logical_type\": \"context\", \"relative_path\": \"README.md\", \"sha256\": \"44690a2d7fc41955720c48da7b6f2dc8de7d006e58d8defbf6fc7e06fa820cc7\"}, {\"content\": \"# Changelog\\n\\n## v0.1.0\\n\\n- Initial formal storyboard skill package.\\n\", \"logical_type\": \"context\", \"relative_path\": \"CHANGELOG.md\", \"sha256\": \"c2b46e2c1f025cb305329d43fdc8ce33dca2a66ea7c4a8e78eb6e465e28478fc\"}, {\"content\": \"# Migration Notes\\n\\nThis package is newly created from approved storyboard requirements.\\nIt is not a migration of an existing formal Storyboard Skill.\\n\", \"logical_type\": \"context\", \"relative_path\": \"MIGRATION-NOTES.md\", \"sha256\": \"77ccd75901e97c91ad276967a0749753a4a17a84a085ef78a7ecad31d6714ad4\"}, {\"content\": \"PyYAML>=6.0\\n\", \"logical_type\": \"context\", \"relative_path\": \"requirements.txt\", \"sha256\": \"71749243f84428fee225bfaa796dca5ef6c1e83a98f6d2a407df615b0390d6fb\"}, {\"content\": \"# Storyboard Rules\\n\\nStoryboard revisions must preserve approved script scene order, shot continuity, and upstream binding.\\n\", \"logical_type\": \"context\", \"relative_path\": \"references/storyboard-rules.md\", \"sha256\": \"11ad719d044211bcd298fa5cd35123988afd30f9ebd564cee6c4f950049cee43\"}, {\"content\": \"# Source Staleness Policy\\n\\nA storyboard revision becomes stale when its source script revision is no longer the current approved revision for the source script artifact.\\n\", \"logical_type\": \"context\", \"relative_path\": \"references/source-staleness-policy.md\", \"sha256\": \"bd735f285125608e74eb9d023b9ffc10ebbc49774a5430d0a243a55169133338\"}, {\"content\": \"# Shot Boundary Policy\\n\\nSplit scenes into shots using stable, source-grounded boundaries.\\n\", \"logical_type\": \"context\", \"relative_path\": \"references/shot-boundary-policy.md\", \"sha256\": \"cd746dd92e506bffb2e5254d8fdffed7287af362e3c828170c3ddd1e0474ff51\"}, {\"content\": \"# Continuity Policy\\n\\nEach shot must record continuity_in and continuity_out values.\\n\", \"logical_type\": \"context\", \"relative_path\": \"references/continuity-policy.md\", \"sha256\": \"d3996b21606e8eabe3ddeef8a6a36f41616916424b3740d5f2d600d37ba7b5d1\"}, {\"content\": \"# Storyboard\\n\\n## 场次：{scene_id}\\n\\n### 镜头 {shot_order}\\n\\n- scene_id: {scene_id}\\n- shot_id: {shot_id}\\n- shot_order: {shot_order}\\n- source_scene_reference: {source_scene_reference}\\n- duration_seconds: {duration_seconds}\\n- shot_size: {shot_size}\\n- camera_angle: {camera_angle}\\n- camera_movement: {camera_movement}\\n- visual_composition: {visual_composition}\\n- character_positions: {character_positions}\\n- character_actions: {character_actions}\\n- emotion_performance: {emotion_performance}\\n- dialogue: {dialogue}\\n- sound_notes: {sound_notes}\\n- continuity_in: {continuity_in}\\n- continuity_out: {continuity_out}\\n\", \"logical_type\": \"context\", \"relative_path\": \"templates/storyboard-outline.template.md\", \"sha256\": \"38bda79d09c72a227d78757c9645a060986fd6c085fea79abbf5369ac38df22c\"}, {\"content\": \"{\\n  \\\"scene_id\\\": \\\"{scene_id}\\\",\\n  \\\"shots\\\": [\\n    {\\n      \\\"scene_id\\\": \\\"{scene_id}\\\",\\n      \\\"shot_id\\\": \\\"{shot_id}\\\",\\n      \\\"shot_order\\\": \\\"{shot_order}\\\",\\n      \\\"source_scene_reference\\\": \\\"{source_scene_reference}\\\",\\n      \\\"duration_seconds\\\": \\\"{duration_seconds}\\\",\\n      \\\"shot_size\\\": \\\"{shot_size}\\\",\\n      \\\"camera_angle\\\": \\\"{camera_angle}\\\",\\n      \\\"camera_movement\\\": \\\"{camera_movement}\\\",\\n      \\\"visual_composition\\\": \\\"{visual_composition}\\\",\\n      \\\"character_positions\\\": \\\"{character_positions}\\\",\\n      \\\"character_actions\\\": \\\"{character_actions}\\\",\\n      \\\"emotion_performance\\\": \\\"{emotion_performance}\\\",\\n      \\\"dialogue\\\": \\\"{dialogue}\\\",\\n      \\\"sound_notes\\\": \\\"{sound_notes}\\\",\\n      \\\"continuity_in\\\": \\\"{continuity_in}\\\",\\n      \\\"continuity_out\\\": \\\"{continuity_out}\\\"\\n    }\\n  ]\\n}\\n\", \"logical_type\": \"context\", \"relative_path\": \"templates/storyboard-outline.template.json\", \"sha256\": \"b9d519cd06e68382550ed862e8f8f5ab32dc9d45cbccf3d208899fb5c4efafb9\"}, {\"content\": \"{\\n  \\\"$schema\\\": \\\"https://json-schema.org/draft/2020-12/schema\\\",\\n  \\\"type\\\": \\\"object\\\",\\n  \\\"required\\\": [\\\"scene_id\\\", \\\"shots\\\"],\\n  \\\"additionalProperties\\\": false,\\n  \\\"properties\\\": {\\n    \\\"scene_id\\\": {\\n      \\\"type\\\": \\\"string\\\",\\n      \\\"minLength\\\": 1\\n    },\\n    \\\"shots\\\": {\\n      \\\"type\\\": \\\"array\\\",\\n      \\\"minItems\\\": 1,\\n      \\\"items\\\": {\\n        \\\"type\\\": \\\"object\\\",\\n        \\\"required\\\": [\\n          \\\"scene_id\\\",\\n          \\\"shot_id\\\",\\n          \\\"shot_order\\\",\\n          \\\"source_scene_reference\\\",\\n          \\\"duration_seconds\\\",\\n          \\\"shot_size\\\",\\n          \\\"camera_angle\\\",\\n          \\\"camera_movement\\\",\\n          \\\"visual_composition\\\",\\n          \\\"character_positions\\\",\\n          \\\"character_actions\\\",\\n          \\\"emotion_performance\\\",\\n          \\\"dialogue\\\",\\n          \\\"sound_notes\\\",\\n          \\\"continuity_in\\\",\\n          \\\"continuity_out\\\"\\n        ],\\n        \\\"additionalProperties\\\": false,\\n        \\\"properties\\\": {\\n          \\\"scene_id\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"shot_id\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"shot_order\\\": {\\\"type\\\": \\\"integer\\\", \\\"minimum\\\": 1},\\n          \\\"source_scene_reference\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"duration_seconds\\\": {\\\"type\\\": \\\"integer\\\", \\\"minimum\\\": 5, \\\"maximum\\\": 15},\\n          \\\"shot_size\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"camera_angle\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"camera_movement\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"visual_composition\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"character_positions\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"character_actions\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"emotion_performance\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"dialogue\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"sound_notes\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"continuity_in\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n          \\\"continuity_out\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1}\\n        }\\n      }\\n    }\\n  }\\n}\\n\", \"logical_type\": \"context\", \"relative_path\": \"schemas/storyboard-outline.schema.json\", \"sha256\": \"66bd14811036d2214979607f261da406b40efcbc77bd768c2f0263cc9ab04895\"}, {\"content\": \"{\\n  \\\"$schema\\\": \\\"https://json-schema.org/draft/2020-12/schema\\\",\\n  \\\"type\\\": \\\"object\\\",\\n  \\\"required\\\": [\\\"source_scene_references\\\", \\\"missing_scene_references\\\", \\\"extra_scene_references\\\"],\\n  \\\"additionalProperties\\\": false,\\n  \\\"properties\\\": {\\n    \\\"source_scene_references\\\": {\\n      \\\"type\\\": \\\"array\\\",\\n      \\\"items\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n      \\\"minItems\\\": 1,\\n      \\\"uniqueItems\\\": true\\n    },\\n    \\\"missing_scene_references\\\": {\\n      \\\"type\\\": \\\"array\\\",\\n      \\\"items\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n      \\\"uniqueItems\\\": true\\n    },\\n    \\\"extra_scene_references\\\": {\\n      \\\"type\\\": \\\"array\\\",\\n      \\\"items\\\": {\\\"type\\\": \\\"string\\\", \\\"minLength\\\": 1},\\n      \\\"uniqueItems\\\": true\\n    }\\n  }\\n}\\n\", \"logical_type\": \"context\", \"relative_path\": \"schemas/storyboard-coverage.schema.json\", \"sha256\": \"6814495e8fd2da8c07670aa09ef6b9d68c59000087ccf0116a676c6757e299a8\"}, {\"content\": \"# Storyboard Design Contract v1\\n\\n## Structure\\n\\n- Markdown only\\n- `# Storyboard` title\\n- `## 场次：{scene_id}` per scene\\n- `### 镜头 {shot_order}` per shot\\n\\n## Required shot fields\\n\\nEach shot must define:\\n\\n- `scene_id`\\n- `shot_id`\\n- `shot_order`\\n- `source_scene_reference`\\n- `duration_seconds`\\n- `shot_size`\\n- `camera_angle`\\n- `camera_movement`\\n- `visual_composition`\\n- `character_positions`\\n- `character_actions`\\n- `emotion_performance`\\n- `dialogue`\\n- `sound_notes`\\n- `continuity_in`\\n- `continuity_out`\\n\\n## Constraints\\n\\n- `duration_seconds` must be between 5 and 15.\\n- `shot_id` must be unique across the chapter.\\n- `shot_order` must be unique within a scene and increase monotonically.\\n- `source_scene_reference` must cover every source scene without inventing new scenes.\\n- No downstream execution terms, shot prompt packages, or platform parameters.\\n\\n## Source binding\\n\\nStoryboard revisions must cite the approved source script revision and its captured approval record in provenance.\\n\", \"logical_type\": \"context\", \"relative_path\": \"contracts/storyboard-design-contract-v1.md\", \"sha256\": \"4b1c8ceec61fdc99c457fe137dfed4102201ebfad1fdc0b95bcbeb90383238a0\"}, {\"content\": \"# Storyboard Approval Contract v1\\n\\nStoryboard approval is allowed only when:\\n\\n1. the storyboard revision is derived from the current approved script revision;\\n2. all required storyboard validators ran and passed;\\n3. no required validator was incorrectly marked not applicable;\\n4. the source script approval record captured at generation time is preserved in provenance;\\n5. the storyboard revision is fresh against the current approved script revision.\\n\\nApproval actions:\\n\\n- `storyboard_approved`\\n- `storyboard_rejected`\\n\\nApproval must not rewrite source provenance after later script approvals.\\n\", \"logical_type\": \"context\", \"relative_path\": \"contracts/storyboard-approval-contract-v1.md\", \"sha256\": \"dd11e4ef08b73b5bb4ac2cb129b2374c5fd4cae4b54f09b46914cb7ef400d970\"}, {\"content\": \"FORBIDDEN_PROJECT_NAME\\nFORBIDDEN_PROJECT_LINE\\nFIXED_SAMPLE_BEAT_ID\\n\", \"logical_type\": \"context\", \"relative_path\": \"runtime-validators/forbidden-terms.txt\", \"sha256\": \"0bd8c989300737eb12bb061db5c0ea271f5a89a20abc6b728ce1b3c273cdbafa\"}], \"inputs\": {\"characters\": \"# 角色设定档案\\n\\n## 元数据\\n- **作品**：商海沉浮·釜底抽薪篇\\n- **宪法版本**：v2.0.0\\n- **创建日期**：2026-06-16\\n- **基于来源**：宪法、规格书、创作计划、30章实际内容\\n\\n---\\n\\n## 一、主角\\n\\n### 沈清荷（姐姐·商道之刃）\\n\\n#### 基本信息\\n- **身份**：沈家长女，商业掌舵人\\n- **年龄**：约二十岁（及笄之后，议亲阶段）\\n- **父亲**：已故（生前是商人，教沈清荷经商）\\n- **母亲**：未出场（人丁单薄的设定）\\n\\n#### 外貌特征\\n- 手指常年握笔，指间有薄茧\\n- 书房窗外的桂花树是她的精神锚点\\n\\n#### 性格层次\\n\\n**表层（对外）**：\\n- 沉稳、话少、持重\\n- 渣男眼中：\\\"温柔、好哄、听话的未婚妻\\\"\\n\\n**中层（对内）**：\\n- 精于算计、冷静如棋手\\n- 凡事用账本说话\\n- 愤怒时不吼叫，在账本上记一笔\\n\\n**深层（核心）**：\\n- 前世被利用至死，重生后的觉悟：爱情只是工具，财权才是根本\\n- 对妹妹的愧疚与保护欲并存\\n- 复仇不是情绪宣泄，是精心策划的商业战争\\n\\n#### 核心能力\\n- 渠道掌控、资源调配\\n- 对数字和账目过目不忘\\n- 前世掌握盐铁渠道，这一世知道未来十年商业风向\\n- 训练有素的商业直觉\\n\\n#### 标志性行为\\n| 动作 | 触发时机 | 在文中的应用 |\\n|------|---------|------------|\\n| 拨动算盘珠 | 重大决定前 | 第1章、第6章、第20章、第30章 |\\n| 在账本上记一笔 | 愤怒/记仇时 | 反复出现，贯穿全书 |\\n| 给妹妹夹菜 | 开心时 | 姐妹互动场景 |\\n| \\\"这笔账，划不来\\\" | 判断得失时 | 金句模式 |\\n\\n#### 前世经历\\n- 被渣男利用商业才能，帮他平步青云登上户部高位\\n- 被渣男挑拨离间，以为妹妹要毒杀自己\\n- 临死前看到渣男搂着丞相之女林婉兮，亲口承认：\\\"我只是借你们沈家的钱袋子，铺我的青云路。\\\"\\n- 被毒杀而死\\n\\n#### 今世成长弧线\\n\\n| 阶段 | 章节 | 状态 |\\n|------|------|------|\\n| 觉醒期 | 第1-3章 | 从震惊到清醒，与妹妹相认，确立复仇同盟 |\\n| 布局期 | 第4-10章 | 截胡生意、记账、设陷阱，表面演痴情未婚妻 |\\n| 发力期 | 第11-16章 | 改良制盐技术，开辟新渠道，蚕食渣男经济命脉 |\\n| 收网期 | 第17-20章 | 引导渣男入局，伪造投资人，准备证据 |\\n| 决裂期 | 第21-28章 | 送匿名信、当堂对质、撕婚书、烧婚约 |\\n| 终局 | 第29-30章 | 拿下皇商资格，掌管三个盐铺，成为独立女商人 |\\n\\n#### 随身道具\\n- **算盘**（核心道具）：第1章结尾第一次拨动 → 第30章最后放下\\n- **账本**（秘密武器）：记录了渣男每一笔贪污、每一笔借款\\n\\n---\\n\\n### 沈清莲（妹妹·人心之网）\\n\\n#### 基本信息\\n- **身份**：沈家次女，社交操盘手\\n- **年龄**：约十七八岁\\n- **训练经历**：十年\\\"察言观色、撒娇卖痴\\\"的训练（第2章自述）\\n\\n#### 外貌特征\\n- 爱笑，笑容天真烂漫\\n- 随身携带梅花团扇，绣线已有些松了（暗示使用频率之高）\\n\\n#### 性格层次\\n\\n**表层（对外）**：\\n- 天真烂漫、笑语晏晏\\n- 渣男眼中：\\\"崇拜自己的小姨子，好利用\\\"\\n\\n**中层（对内）**：\\n- 通透机敏、话里藏刀\\n- 最擅长用无辜的语气说出最致命的信息\\n- 对姐姐真诚，对敌人演戏\\n\\n**深层（核心）**：\\n- 前世痴迷渣男，被利用后惨死\\n- 重生后最痛的不是被渣男害死，而是前世与姐姐反目\\n- 她的复仇武器不是算盘，是人心\\n\\n#### 核心能力\\n- 人际网络构建、情报收集\\n- 十年社交训练：记住每个人的生辰、软肋和欲望\\n- 前世广结善缘，掌握大量人脉情报\\n- 借力打力——不需要亲自出手，让敌人自相残杀\\n\\n#### 标志性行为\\n| 动作 | 触发时机 | 在文中的应用 |\\n|------|---------|------------|\\n| 团扇掩住嘴角笑意 | 说完致命信息后 | 第3章、第7章、第22章 |\\n| 笑语晏晏，话里藏刀 | 社交场合 | 贯穿全书 |\\n| \\\"哎呀，这可不巧了么\\\" | 算计得逞时 | 金句模式 |\\n| 对姐姐真笑，对敌人假笑 | 角色切换时 | 社交场合与私下对比 |\\n\\n#### 前世经历\\n- 被渣男甜言蜜语蒙蔽，前世与姐姐争风吃醋\\n- 四处炫耀未婚夫深情，结果同样被利用至死\\n- 重生方式：做了一场噩梦，梦中经历了前世的一切\\n\\n#### 今世成长弧线\\n\\n| 阶段 | 章节 | 状态 |\\n|------|------|------|\\n| 觉醒期 | 第1-3章 | 从噩梦中醒来，与姐姐对视即达成默契 |\\n| 布局期 | 第4-10章 | 扮演崇拜渣男的小姨子，散播假消息 |\\n| 发力期 | 第11-16章 | 社交策反，拉拢刘德旺，接触王夫人 |\\n| 收网期 | 第17-20章 | 安排假投资人方老板，信息误导渣男 |\\n| 决裂期 | 第21-28章 | 当面翻脸，公开揭露渣男真面目 |\\n| 终局 | 第29-30章 | 创办清莲书院，三顾茅庐请方先生，完成独立 |\\n\\n#### 随身道具\\n- **团扇**（核心道具）：梅花绣纹，绣线已松，每次说完致命信息掩嘴笑\\n- **社交笔记**（暗线道具）：她能记住每个人的生辰、软肋和欲望\\n\\n---\\n\\n## 二、反派\\n\\n### 顾长渊（渣男世子）\\n\\n#### 基本信息\\n- **身份**：侯府世子（爵位继承人）\\n- **父亲**：老侯爷（仅侧面提及，第27章砸书房）\\n- **母亲**：侯夫人（仅侧面提及，第27章清理院子）\\n- **外表**：温润如玉，常穿月白色长衫\\n- **年龄**：约二十出头\\n\\n#### 性格特征\\n\\n**表面**：\\n- 温文尔雅，谦谦君子\\n- 谈吐风雅，举止得体\\n- 让人放下戒心的\\\"好人\\\"形象\\n\\n**内核**：\\n- 极度自负，看不起商贾出身的沈家\\n- 精于算计，商品是\\\"爱情\\\"\\n- 核心信念：\\\"女人嘛，好哄\\\"、\\\"女人终究是女人\\\"\\n- 贪婪且轻视女性——这是他致命的盲区\\n\\n#### 前世经历\\n- 利用沈家姐妹的资源和感情，平步青云登上户部高位\\n- 挑拨离间让两姐妹互斗至死\\n- 最终搂着丞相之女林婉兮，亲口承认利用\\n- \\\"我只是借你们沈家的钱袋子，铺我的青云路。\\\"\\n\\n#### 致命弱点\\n- 自负：至死不信女人能有翻天的智慧\\n- 贪婪：挪用公款、多线操作、越陷越深\\n- 轻视女性：即使\\\"诸事不顺\\\"，也不怀疑姐妹\\n- 真商人假君子：嘴上风雅，心里全是生意\\n\\n#### 罪行清单（实际内容统计）\\n| 罪行 | 金额/内容 | 证据 |\\n|------|---------|------|\\n| 盐铺账目造假 | 近2000两 | 账本中\\\"特定\\\"\\\"杂项\\\"条目 |\\n| 挪用户部公款 | 13000两 | 周书办被查获的私账 |\\n| 向沈家多次借款 | 7000+两 | 借据（沈清荷保管） |\\n| 虚假投资人协议 | 2000两 | 合伙契书（沈清荷保留） |\\n| 抬高盐铺采购价中饱私囊 | 数额不明 | 赵四提供的证据 |\\n\\n#### 人物弧线（权力下坠曲线）\\n\\n| 章节 | 状态 | 关键事件 |\\n|------|------|---------|\\n| 第1-3章 | 志得意满 | 两个女人为我争风吃醋，一切尽在掌握 |\\n| 第4-9章 | 隐隐不安 | 南货被截、传言四起，但归因于运气不好 |\\n| 第10章 | 信心巅峰 | 拿下漕运资格，以为大计将成 |\\n| 第13章 | 开始怀疑 | 派人调查，被姐妹完美伪装骗过 |\\n| 第16-17章 | 焦虑加深 | 盐铺收入下降、粮商催款 |\\n| 第18-19章 | 假装镇定 | 查账通过、投资到位，又放心了 |\\n| 第20章 | 恍然大悟 | 三个关键人物同时消失，但不敢信是沈清荷 |\\n| 第21-23章 | 疯狂补救 | 四处借钱被拒、周书办被抓、龙井茶出现在书房 |\\n| 第24章 | 真相大白 | 姐妹当面对质，揭露一切 |\\n| 第25章 | 彻底崩溃 | 公堂定罪、林婉兮冷眼、锒铛入狱 |\\n| 第26-27章 | 无力挣扎 | 反咬失败、削爵、发配北疆 |\\n| 第28章 | 彻底出局 | 婚约被撕毁、侯府试图挽回被拒 |\\n\\n#### 创作铁律\\n- ✅ 聪明但自负——他不是蠢，是看不起女人\\n- ✅ 在中期之前（第13-19章）察觉有\\\"幕后黑手\\\"但不信是姐妹\\n- ✅ 不洗白——没有\\\"深情无奈\\\"的戏码\\n- ✅ 结局：人财两空，身败名裂，发配边疆\\n\\n---\\n\\n## 三、核心盟友\\n\\n### 赵四（第一个内线）\\n\\n- **身份**：侯府盐铺二掌柜\\n- **年龄**：约三十岁\\n- **工龄**：为侯府工作六年\\n- **性格**：老实本分、不善交际、孝顺\\n- **家庭**：母亲常年咳疾，需要定期抓药；妹妹在绣坊做学徒\\n- **住址**：侯府西边巷子第三家，门口有棵槐树\\n- **被策反方式**：沈清莲亲自登门，承诺沈家铺子的职位、双倍月钱、让他照顾母亲\\n- **作用**：\\n  - 提供盐铺真实账目（揭露顾长渊抬高采购价中饱私囊）\\n  - 向顾长渊提供假情报（雪盐日产量只有200斤，实际500斤）\\n  - 成为姐妹在侯府内部的眼线\\n- **出场**：第8章（策反）、第16章（提供假情报）\\n\\n### 陈伯远（制盐伙伴）\\n\\n- **身份**：盐匠，手艺人\\n- **性格**：老实、技术好但不善经营\\n- **地点**：原作坊在城外东边五六里，后迁至城东运河边\\n- **技术**：只会做灰盐（低价）\\n- **被提升方式**：沈清荷带着\\\"豆浆法\\\"找上门——卤水中加豆浆去除杂质，产出纯白如雪的\\\"雪盐\\\"\\n- **合作关系**：沈清荷提供资金和销路，陈伯远提供技术，五五分账\\n- **发展轨迹**：\\n  - 第11章：小作坊，几口锅\\n  - 第14章：六口大锅，日产500斤\\n  - 第29章：八口锅→二十口锅，供应官盐\\n- **出场**：第11章、第14章、第29章\\n\\n### 刘德旺（粮商盟友）\\n\\n- **身份**：京城粮商\\n- **资历**：与侯府合作八年\\n- **性格**：稳重、话少、守信、讲义气\\n- **与渣男关系**：顾长渊欠他1800两粮款未还，早已不满\\n- **被策反方式**：沈清莲在赏春宴上主动接触，暗示沈家更可靠\\n- **策反条件**：沈家所有粮食业务过他的手，市价交易，不拖欠货款\\n- **额外作用**：成为姐妹监控渣男动向的暗线\\n- **出场**：第12章（初次接触）、第15章（正式入伙）\\n\\n### 方先生（书院教师）\\n\\n- **身份**：女性学者，曾在江南书院任教，退休回京\\n- **出场**：第29章（沈清莲三顾茅庐，第三次带自酿桂花酒才请动）\\n- **作用**：清莲书院第一位先生，象征沈清莲的事业独立\\n\\n---\\n\\n## 四、次要角色\\n\\n### 渣男阵营（被姐妹击败的一方）\\n\\n| 姓名 | 身份 | 与渣男关系 | 结局 |\\n|------|------|----------|------|\\n| 孙旺财 | 东市掮客 | 渣男找的中介 | 被沈清荷收买后消失（第20章） |\\n| 周书办 | 户部书办，二十年老吏 | 渣男贪污同谋 | 匿名信举报后被逮捕（第23章） |\\n| 吴管事 | 侯府管家 | 替渣男跑腿调查 | 调查无果 |\\n| 钱管事 | 侯府账房，十年老仆 | 忠于侯府 | 给渣男最后500两私房钱（第21章） |\\n| 王夫人 | 王御史之妻 | 社交圈信息来源 | 被沈清莲利用传播谣言 |\\n| 张侍郎太太 | 吏部张侍郎之妻 | 社交圈信息来源 | 同上 |\\n| 周三小姐 | 周家小姐 | 社交圈信息来源 | 同上 |\\n| 吴老板 | 渣男远亲，西城丝绸商 | 曾受侯府两千两救命钱 | 拒绝借钱（第21章） |\\n| 林老板 | 渣男前生意伙伴 | 曾被渣男帮过拿下河道工程 | 拒绝借钱：\\\"你拿什么还\\\"（第21章） |\\n| 陈员外郎 | 户部官员 | 收过渣男礼 | 拒绝帮忙拖延调查（第22章） |\\n\\n### 中立/背景角色\\n\\n| 姓名 | 身份 | 作用 |\\n|------|------|------|\\n| 周老板 | 金陵周记商行 | 渣男想买他的南货，被沈清荷截胡（第4章） |\\n| 马老板 | 漕运批文持有者 | 卖了一个批文（沈清荷通过中间人买下） |\\n| 王掌柜 | 城南王家杂货铺 | 雪盐第一个零售点（第14章） |\\n| 王主事 | 户部主事 | 渣男想贿赂的对象之一 |\\n| 户部侍郎 | 户部二把手 | 收到匿名信、主持审判（第23、25章） |\\n| 老侯爷 | 顾长渊之父 | 仅侧面提及，儿子事发后砸书房（第27章） |\\n| 侯夫人 | 顾长渊之母 | 仅侧面提及，清理儿子院落（第27章） |\\n| 刘管事 | 侯府管家，二十年老仆 | 替老侯爷送信试图挽回婚约（第28章） |\\n| 李夫人 | 西城李府主人 | 第7章赏花宴主办者 |\\n| 周侍郎 | 吏部官员 | 第2章被沈清莲提及有私生子 |\\n\\n---\\n\\n## 五、角色关系图谱\\n\\n```\\n                    前世记忆（共同仇人）\\n                         ↓\\n    ┌──────────────────────────────────────┐\\n    │                                      │\\n┌───────┐  姐妹同盟（坚不可摧）  ┌───────┐\\n│沈清荷  │ ←────────────────→  │沈清莲  │\\n│商道之刃 │   算账 / 算人       │人心之网 │\\n└───┬───┘                      └───┬───┘\\n    │                              │\\n    │ 截胡生意                     │ 策反拉拢\\n    │ 改良制盐                     │ 散布谣言\\n    │ 设陷阱                       │ 安插内线\\n    │                              │\\n    ▼                              ▼\\n┌─────────────────────────────────────────┐\\n│              顾长渊（渣男）              │\\n│         侯府世子/月白长衫/温润如玉        │\\n│           致命弱点：轻视女性              │\\n│                                          │\\n│  ←── 经济封锁（截胡/架空/造假）         │\\n│  ←── 社交孤立（策反/谣言/内线）         │\\n│  ←── 法律打击（匿名信/借据/账本证据）    │\\n└─────────────────────────────────────────┘\\n    │\\n    │ 被击败后\\n    ▼\\n  削爵 + 发配北疆 + 终身不得回京\\n```\\n\\n### 姐妹分工矩阵\\n\\n| 维度 | 沈清荷 | 沈清莲 |\\n|------|--------|--------|\\n| 核心武器 | 算盘（算账） | 团扇（算人） |\\n| 战场 | 商场 | 社交场 |\\n| 攻击方式 | 截胡/架空/垄断 | 策反/谣言/收买 |\\n| 关键盟友 | 陈伯远、周老板 | 赵四、刘德旺、方先生 |\\n| 金句 | \\\"这笔账，划不来\\\" | \\\"哎呀，这可不巧了么\\\" |\\n| 终局成就 | 皇商掌权人 | 女子书院创办人 |\\n\\n### 情感纽带\\n- **姐妹情**：通过动作细节表达——夹菜、对视、挡在身前、共饮酒\\n- **对渣男**：零情感，纯工具，每一句甜言蜜语都是台词\\n- **对盟友**：以利相交，同时给予尊重——不是施舍，是合作\\n\\n---\\n\\n## 六、角色一致性检查清单\\n\\n### 沈清荷\\n- [x] 是否每次愤怒都在账本上记一笔而非吼叫？\\n- [x] 是否重大决定前都拨动了算盘？\\n- [x] 是否用数字和账本说话而非情绪？\\n- [x] 是否对妹妹绝对信任？\\n\\n### 沈清莲\\n- [x] 是否每次说到致命信息都用团扇掩笑？\\n- [x] 是否对外人笑里藏刀，对姐姐笑里真诚？\\n- [x] 是否发挥了\\\"记住每个人的软肋\\\"的能力？\\n- [x] 是否对渣男零真情？\\n\\n### 顾长渊\\n- [x] 是否始终轻视女性？\\n- [x] 是否第20章前都没怀疑姐妹？\\n- [x] 是否没被洗白？\\n- [x] 是否结局符合\\\"人财两空、身败名裂\\\"？\\n\\n*创建时间：2026-06-16*\\n*基于：宪法v2.0.0 + 规格书v1.3.0 + 创作计划v1.0.0 + 30章实际内容*\", \"production_brief\": \"项目类型：\\n\\n- 古装女性权谋短剧\\n- 重生\\n- 宅斗\\n- 家族利益博弈\\n- 商道权谋\\n- 人物之间的试探、隐忍、算计与反击\\n\\n类型边界：\\n\\n- “权谋”表示人物关系、利益冲突和叙事节奏。\\n- 如原文不存在皇宫、后宫、妃嫔、皇帝或朝廷线，不得擅自增加。\\n- 不得为了制造“宫斗感”改变原文世界观和人物身份。\\n\\n改编方向：\\n\\n- 真人短剧叙事\\n- 冲突清晰\\n- 节奏紧凑\\n- 情绪递进明确\\n- 保留人物核心动机\\n- 内心描写优先转化为动作、微表情、停顿、呼吸和视线变化\\n- 不得为了追求爽感篡改原文事实\\n- 不得确认 unknown_do_not_invent 内容\\n\\n视觉方向：\\n\\n- 真人写实风格\\n- 古装影视剧质感\\n- 真实人物皮肤纹理\\n- 真实服饰和织物纹理\\n- 低饱和、柔和电影布光\\n- 精致但不过度仙侠化\\n- 非动漫\\n- 非二次元\\n- 非游戏建模\\n- 场景、服饰和道具符合人物身份及故事环境\\n\\n生产约束：\\n\\n- 主要画幅为 16:9\\n- 后续 LibTV 视频 Unit 必须为 5–15 秒\\n- 人物脸部与骨相保持一致\\n- 服装、发型、配饰保持连续\\n- 场景布局和家具位置保持一致\\n- 人物站位、左右关系和视线保持一致\\n- 光源方向和时间状态保持一致\\n- 前后视频节点动作必须连续\", \"series_canon\": \"# 世界观设定\\n\\n## 元数据\\n- **作品**：商海沉浮·釜底抽薪篇\\n- **宪法版本**：v2.0.0\\n- **创建日期**：2026-06-16\\n- **世界观基调**：偏架空爽文（商业逻辑为主，朝堂为背景板）\\n- **来源**：规格书澄清#1 + 30章实际内容\\n\\n---\\n\\n## 一、时代背景\\n\\n### 王朝设定\\n- **国号**：未命名（架空王朝，不深究历史朝代）\\n- **政治结构**：君主制 + 六部制（仿古，不考据具体年代）\\n- **核心设定**：商业发达，盐铁等重要物资半官营半私营\\n- **特点**：爵位世袭、科举入仕并存；官商合作普遍\\n\\n### 创作原则\\n- 朝堂只是背景板——政治斗争不展开，焦点始终在商战\\n- 法律、官职、商业规则服务于故事，不追求历史考据\\n- 架空自由度——可以自创商业规则，不需对应真实朝代\\n\\n---\\n\\n## 二、政治体系\\n\\n### 爵位层级（简化版）\\n\\n| 爵位 | 说明 | 故事中对应 |\\n|------|------|----------|\\n| 侯府 | 中高层贵族，世袭罔替 | 顾长渊家族 |\\n| 丞相府 | 文官之首 | 林婉兮之父（外任中） |\\n\\n**爵位继承**：\\n- 世子是法定继承人\\n- 犯罪可被削去世子爵位（顾长渊的结局）\\n- 老侯爷在世时，侯府仍由他名义上掌管\\n\\n### 朝廷六部（简化版）\\n\\n| 部门 | 职能 | 故事中涉及 |\\n|------|------|----------|\\n| 户部 | 财政、漕运、盐铁、税收 | 核心舞台 |\\n| 吏部 | 官员任免 | 间接涉及（张侍郎） |\\n| 工部 | 工程、河道 | 间接涉及（林老板的河道工程） |\\n\\n### 户部官僚层级（故事实际出现）\\n\\n| 职位 | 品级 | 职能 | 代表人物 |\\n|------|------|------|---------|\\n| 户部侍郎 | 三品 | 户部二把手，主持审判 | 审判顾长渊 |\\n| 户部郎中 | 五品 | 司局长官 | 顾长渊的目标职位 |\\n| 户部主事 | 六品 | 处级官员 | 王主事 |\\n| 户部员外郎 | 从五品 | 司局副职 | 陈员外郎 |\\n| 户部书办 | 不入流 | 管账的文书吏 | 周书办（二十年老吏） |\\n\\n**官职体系说明**：\\n- 郎中是实权职位，管一司事务\\n- 书办虽无品级，但掌握账目命脉，实际权力不小\\n- 进入六部需要\\\"运作\\\"——送礼、攀关系、找引荐人\\n\\n---\\n\\n## 三、商业体系\\n\\n### 货币政策\\n\\n| 单位 | 说明 | 实际购买力参考 |\\n|------|------|-------------|\\n| 文 | 铜钱，最小单位 | 1斤灰盐=15文；1斤雪盐=40文 |\\n| 两（银子） | 银两，基本交易单位 | 1两≈1000文；一个人月钱约3-5两 |\\n| 银票 | 钱庄发行的纸币 | 大额交易用，京城最大钱庄最可信 |\\n\\n**购买力锚定**：\\n- 一个盐铺二掌柜月钱：数两银子\\n- 漕运批文转让价：1800两\\n- 渣男挪用户部公款总额：13000两（足以发配三千里）\\n- 侯府中人二十年积蓄：500两\\n\\n### 钱庄制度\\n- 京城有主要钱庄若干，最大的那家信誉最高\\n- 银票可跨城兑现\\n- 钱庄也做借贷（有利息，连本带利）\\n- 借据（借据）具有法律效力\\n\\n### 盐业体系\\n\\n#### 盐的种类与等级\\n\\n| 品种 | 品质 | 价格 | 说明 |\\n|------|------|------|------|\\n| 灰盐 | 低 | 15文/斤 | 普通百姓用盐，颜色灰暗 |\\n| 青盐 | 中 | 30文/斤 | 好盐，市面主流 |\\n| 雪盐 | 高 | 40文/斤 | 沈清荷的技术创新，纯白如雪 |\\n\\n#### 制盐技术（实际设定）\\n- **传统工艺**：卤水熬煮，产出灰盐或青盐\\n- **豆浆法（核心创新）**：在卤水中加豆浆，杂质随豆浆沫浮出，撇去后得到纯白结晶\\n- **来源**：南方一本杂记中记载的民间偏方（沈清荷前世记忆）\\n- **技术壁垒**：简单但没人知道——信息差就是商业优势\\n\\n#### 盐铁渠道（权力结构）\\n- 盐作为必需品商品，由政府控制流通\\n- 贵族和官员可以通过\\\"关系\\\"获得盐的经营权\\n- 侯府掌握盐铺——这是一种权力资源\\n- 变相垄断：有权有势者垄断最好的渠道\\n\\n#### 盐引制度\\n- 盐引是政府颁发的食盐经营许可证\\n- 持有盐引者可合法经营食盐\\n- 皇商资格是最高级别的盐引\\n\\n### 漕运体系\\n\\n#### 漕运（运河运输系统）\\n- 政府控制的粮食物资运输网络\\n- 核心路线：江淮→京城（运河沿线）\\n\\n#### 供应商准入\\n- 需要\\\"供应商资格\\\"（批文），有限额——\\\"一个萝卜一个坑\\\"\\n- 获得方式：购买、继承、或者通过关系运作\\n- 转让价格：1800两左右（故事中马老板卖批文的价格）\\n\\n#### 运营成本\\n- 租船费 + 雇船工 + 码头仓库租赁 + 沿途关卡过路费\\n- 一条批文年收入可达上万两\\n- 但前期投入大，现金流压力重\\n\\n#### 盈利模式\\n- 政府支付固定运费\\n- 同时可夹带部分私货（灰色地带）\\n- 关键在于压低运营成本\\n\\n### 其他主要产业\\n\\n| 产业 | 经营模式 | 故事中涉及 |\\n|------|---------|----------|\\n| 南货（金陵） | 丝绸、茶叶、干货 | 第4章截胡的第一单 |\\n| 粮食 | 城中有多家粮商 | 刘德旺的粮铺 |\\n| 木材 | 河道工程 | 渣男帮林老板拿河道工程 |\\n| 丝绸 | 西城多家铺子 | 吴老板是侯府远亲 |\\n| 杂货 | 油盐酱醋 | 王掌柜的王家杂货铺 |\\n\\n### 商业规则\\n\\n#### 账目制度\\n- 店铺必须记流水账（流水账）\\n- 账目分类：进项（收入）、支出、\\\"特定\\\"（指定用途）、\\\"杂项\\\"、\\\"人情往来\\\"、\\\"采买\\\"、\\\"其他\\\"\\n- \\\"特定\\\"和\\\"杂项\\\"是常见的造假科目（顾长渊即在此做手脚）\\n- 账册可作为法律证据\\n\\n#### 合伙方式\\n- 五五分账（最常见）\\n- 干股（不出钱只出人/技术，按约定比例分利润）\\n- 合伙契书：写明投入、分成、退出条件\\n- 沈清荷的合伙人模式：她出资金和销路，陈伯远出技术，五五分\\n\\n#### 统一定价策略\\n- 沈清荷的雪盐统一零售价40文/斤\\n- 避免各铺子恶性竞价\\n- 树立品牌形象：雪盐=好盐=贵得有道理\\n\\n#### 中介（掮客）体系\\n- 东市等地有专门的中介人\\n- 撮合买卖双方，收取佣金\\n- 孙旺财是典型的中介：人脉广但不专，谁给钱帮谁\\n\\n---\\n\\n## 四、社会结构\\n\\n### 阶层\\n| 阶层 | 代表 | 特征 |\\n|------|------|------|\\n| 贵族 | 侯府、丞相府 | 世袭爵位，有特权 |\\n| 官员 | 户部侍郎、书办 | 有实权但非世袭 |\\n| 商人 | 沈家、刘德旺 | 有钱但地位低 |\\n| 手艺人 | 陈伯远 | 凭手艺吃饭 |\\n| 平民 | 赵四一家 | 工薪阶层 |\\n\\n### 商人的社会地位\\n- 重农抑商的传统仍在，商人有钱但没地位\\n- 商人通过与贵族联姻来\\\"洗白\\\"身份——顾长渊与沈清荷的婚约本质是侯府拿爵位换沈家财富\\n- 皇商资格算是商人的最高荣誉（沈清荷第29章获得）\\n\\n### 女性的社会处境\\n- 未出阁的姑娘主要职责：嫁人\\n- 管理家族生意是例外（因沈家父母不在/无能，姐妹当家）\\n- 女子书院是突破性的新事物（沈清莲第29章创办）\\n- 清莲书院的核心理念：\\\"读书不是为了嫁人。是为了让你们以后——有的选。\\\"\\n\\n---\\n\\n## 五、婚约与法律\\n\\n### 婚约制度\\n- 议亲（谈婚论嫁）→ 定亲 → 婚约成立\\n- 婚书是正式文书，红纸黑字，盖双方家族印章\\n- 毁约需要正当理由（如一方犯罪被削爵——沈清荷以此为由撕毁婚书）\\n\\n### 司法制度（简化）\\n\\n**举报途径**：\\n- 匿名信可以触发调查（沈清荷向户部侍郎送匿名信）\\n- 附带证据的举报更有分量\\n- 门房接收信件后层层传递\\n\\n**审判程序**：\\n- 户部大堂审理（第25章）\\n- 原告方出示证据\\n- 被告方认罪或辩护\\n- 数罪并罚\\n\\n**刑罚体系**：\\n| 罪行 | 惩罚 |\\n|------|------|\\n| 挪用户部公款 | 革职 + 发配充军 |\\n| 伪造账目 | 计入从重情节 |\\n| 贪墨铺银 | 削去爵位 |\\n| 贪污万两以上 | 发配三千里，终身不得回京 |\\n| 数罪并罚 | 叠加处罚 |\\n\\n---\\n\\n## 六、地理环境\\n\\n### 京城及周边\\n\\n```\\n                        北疆（流放地）\\n                           ↕ 数千里\\n                        京城（核心舞台）\\n                       ↙  ↓  ↘\\n               西城区   皇城区   东城区\\n              (李府等)  (户部等)  (东市/码头/\\n                                   运河/书院)\\n                           ↓\\n                        江淮地区\\n                        (运河沿线)\\n                           ↓\\n                        金陵（南京）\\n                   （南货集散地，两天路程）\\n                           ↓\\n                        江南\\n                  （沈家庄园、方先生故地）\\n```\\n\\n### 主要地点汇总\\n\\n#### 沈家\\n- 书房（沈清荷的核心场景）：窗户对着桂花树，有暗格藏漕运批文\\n- 后院亭子：姐妹饮酒、会客、最终场景\\n- 海棠树：婚约灰烬最终撒落之处\\n- 厅堂：接待客人、烧毁婚书\\n\\n#### 侯府\\n- 书房（顾长渊的核心场景）\\n- 盐铺（最大的那家）：赵四在此工作\\n- 侧门/巷子：渣男的秘密出入通道\\n\\n#### 商业区\\n- 东市：掮客活跃、王家杂货铺所在地\\n- 码头：城东运河边，漕运装卸处\\n- 城东运河边：陈伯远扩建后的新作坊\\n\\n#### 官署\\n- 户部大堂：审判场所\\n- 户部侧厢房：周书办工作处\\n- 户部门房值班室：匿名信送达处\\n\\n#### 社交场所\\n- 城西李府：赏花宴\\n- 张侍郎府：赏春宴\\n- 锦绣阁（东城丝绸铺）：沈清莲与王夫人的偶遇地点\\n\\n#### 女性事业空间\\n- 清莲书院（东城）：前退休官员旧宅，院里有槐树\\n- 陈伯远盐坊（城外→运河边）：从小作坊到大工场\\n\\n---\\n\\n## 七、文化习俗\\n\\n### 社交礼仪\\n- 初次见面递\\\"帖子\\\"（名帖）\\n- 做客带礼物（绸料等）\\n- 社交场合：赏花宴、赏春宴是核心社交场景\\n- 贵妇圈是信息流通渠道——沈清莲的主要战场\\n\\n### 送礼文化\\n- 桂花糕（天香楼）：男女之间送，有暧昧意味\\n- 龙井茶（上等）：顾长渊案发时出现在书房，是姐妹的暗示\\n- 桂花酒（自酿）：沈清莲三顾茅庐请方先生的诚意\\n- 绸料：社交场合的标准伴手礼\\n\\n### 时间标记\\n- 故事时间跨度：约一年（春天→次年春/夏）\\n- 月份：正月、三月、四月、五月、六月均有出现\\n- 花卉轮回：桂花打苞→满开→花落；海棠花开花谢；牡丹盛开\\n\\n---\\n\\n## 八、经济世界观核心规则\\n\\n### 1. 信息差即为权力\\n- 沈清荷利用前世记忆知道漕运批文要转手\\n- 沈清莲知道每个人的软肋和秘密\\n- \\\"豆浆法\\\"在书中就有，但别人不知道\\n- 姐妹的复仇本质：用信息差碾压权力差\\n\\n### 2. 账目即为武器\\n- 每一笔账都是证据\\n- 沈清荷的账本记录了渣男全部罪行\\n- \\\"特定\\\"、\\\"杂项\\\"是贪污的入口\\n- 账目可以在公堂上作为呈堂证供\\n\\n### 3. 渠道即为命脉\\n- 控制渠道等于控制市场\\n- 盐铁渠道被侯府垄断 → 沈清荷开辟雪盐渠道 → 架空侯府\\n- 漕运渠道是渣男的大计划 → 姐妹从中设陷阱\\n- 粮食渠道被策反 → 渣男断供\\n\\n### 4. 人情即为资本\\n- 沈清莲的核心竞争力\\n- 记住每个人的软肋和欲望 → 精准策反\\n- 真诚对待赵四、刘德旺 → 建立非交易性信任\\n- 债主对渣男不好 ≠ 盟友对姐妹好，关键在\\\"怎么对待人\\\"\\n\\n---\\n\\n## 九、写作约束\\n\\n### 世界观的\\\"留白\\\"策略\\n- 不交代王朝的具体国号、帝号——因为不重要\\n- 不细说六部运作的细节——需要什么设定什么\\n- 不展开朝堂政治——始终以商业博弈为主\\n- 不加入魔法/修仙/系统——纯现实商战（虽然架空）\\n\\n### 架空爽文的自由度\\n- 可以自创商业规则、法律条文、官职体系\\n- 不需要严格考据历史——因为本来就不是历史小说\\n- 逻辑自洽 > 历史真实\\n- 爽感优先——但要在逻辑合理的范围内\\n\\n---\\n\\n*创建时间：2026-06-16*\\n*基于：规格书v1.3.0 + 创作计划v1.0.0 + 30章实际内容*\\n*宪法合规：偏架空爽文（澄清#1），朝堂为背景板*\", \"source_run_id\": \"b360d68e225c4e6da68f491d5d044024\", \"source_script_approval_record\": {\"action\": \"script_approved\", \"artifact_id\": \"shengsi-chapter-001\", \"created_at\": \"2026-06-28T12:48:03.895524Z\", \"note\": \"\", \"record_id\": \"191fd857c39147108ace296578e3bc7b\", \"reviewer\": \"verifier\", \"revision_id\": \"c37329ee465c464b99bc5a57b690983f\", \"sequence\": 1}, \"source_script_approval_record_id\": \"191fd857c39147108ace296578e3bc7b\", \"source_script_artifact_id\": \"shengsi-chapter-001\", \"source_script_content_hash\": \"ad27a58ce8d58611ca45e6ac40186a2a3c22d6ce04071000ed04755bf5f1dd3a\", \"source_script_markdown\": \"# Mock Drama Script Revision\\n\\nruntime_model: mock-script\\nsource_basis: manifest\\n\\n## Scene: 1-1\\n\\n【画面】\\n女主在清晨醒来，意识到命运重启。\\n\\n【动作】\\n她检查身边物件，确认眼前不是幻觉。\\n\\n【台词】\\n女主：这一世，我要先看清局。\\n\\n## Scene: 1-2\\n\\n【画面】\\n账册摊开，旧日线索重新浮现。\\n\\n【动作】\\n她整理证据，把危险关系和家族账目分开标记。\\n\\n【台词】\\n女主：账不会骗人，人心才会。\\n\", \"source_script_revision_id\": \"c37329ee465c464b99bc5a57b690983f\"}, \"output_contract\": {\"format\": \"markdown\", \"parser_version\": \"storyboard-markdown-v1\", \"profile\": \"storyboard-markdown-mvp-v1\", \"supported_artifacts\": [\"storyboard_markdown\"], \"unsupported_bundle_artifacts\": [\"storyboard_json_bundle\", \"shot_prompt_package\", \"visual_asset_binding_package\", \"libtv_execution_package\", \"agnes_execution_package\"]}, \"request_format_version\": \"runtime-request-v1\", \"runtime_config\": {\"model\": \"mock-storyboard\", \"provider\": \"mock\", \"timeout_seconds\": 60}, \"skill\": {\"execution_profile\": \"storyboard-markdown-mvp-v1\", \"package_hash\": \"347b27cfeb0b08c7d1acf825daacd6723f194d933ed34c0bdd18d821f3478230\", \"skill_id\": \"ai-drama-storyboard-design-skill\", \"version\": \"v0.1.0\"}, \"skill_instruction\": {\"content\": \"# AI Drama Storyboard Design Skill v0.1.0\\n\\n## Purpose\\n\\nConvert an approved drama script revision into a creator-facing storyboard revision with shot-level continuity, source coverage, and approval traceability.\\n\\n## Scope\\n\\nUse only for storyboard design. Do not emit shot prompts, LibTV packages, visual asset plans, image/video prompts, or execution commands.\\n\\n## Required Inputs\\n\\n- approved script revision\\n- source approval record\\n- `series_canon`\\n- `characters`\\n- `production_brief`\\n\\n## Markdown Contract\\n\\n- Top header: `# Storyboard`\\n- Scene header: `## 场次：{scene_id}`\\n- Shot header: `### 镜头 {shot_order}`\\n- Every shot must include:\\n  - `scene_id`\\n  - `shot_id`\\n  - `shot_order`\\n  - `source_scene_reference`\\n  - `duration_seconds`\\n  - `shot_size`\\n  - `camera_angle`\\n  - `camera_movement`\\n  - `visual_composition`\\n  - `character_positions`\\n  - `character_actions`\\n  - `emotion_performance`\\n  - `dialogue`\\n  - `sound_notes`\\n  - `continuity_in`\\n  - `continuity_out`\\n\\n## Rules\\n\\n- Preserve source scene order and source facts.\\n- Do not add new core plot events.\\n- Every shot duration must be 5-15 seconds.\\n- Every scene shot must bind a stable `source_scene_reference`.\\n- `shot_id` must be stable within the chapter and unique per shot.\\n- `shot_order` must be unique and strictly increasing within each scene.\\n- `continuity_in` and `continuity_out` must describe the immediate transition state.\\n- `character_positions`, `character_actions`, and `emotion_performance` must be explicit for every shot.\\n- Do not mention downstream execution artifacts or terms.\\n\\n## Output\\n\\nWrite creator-facing Markdown storyboard only.\\n\", \"relative_path\": \"SKILL.md\", \"sha256\": \"9eeb47b0494816df974cf44f4b535b89600387e1160041cbe97a4af71537df2b\"}, \"system_instruction\": \"Follow the skill package and return only the requested Markdown Storyboard revision.\"}"
  },
  {
    "test_item": "Package-level Validator",
    "status": "PASS",
    "evidence": "{\"run_status\": \"SUCCEEDED\", \"revision_id\": \"105243129f1d41ae9eb8bb82ab562ac4\", \"genericity\": {\"status\": \"PASS\", \"required\": false, \"stdout\": \"{\\\"final_status\\\": \\\"pass\\\", \\\"error_code\\\": \\\"\\\", \\\"message\\\": \\\"genericity valid\\\", \\\"forbidden_term_count\\\": 3}\\n\", \"stderr\": \"\", \"report\": {\"final_status\": \"pass\", \"error_code\": \"\", \"message\": \"genericity valid\", \"forbidden_term_count\": 3}}, \"statuses\": {\"storyboard_structure\": \"NOT_APPLICABLE\", \"storyboard_duration\": \"NOT_APPLICABLE\", \"storyboard_source_coverage\": \"NOT_APPLICABLE\", \"storyboard_continuity\": \"NOT_APPLICABLE\", \"genericity\": \"PASS\"}}"
  },
  {
    "test_item": "GitHub CI",
    "status": "PASS",
    "evidence": ".github/workflows/storyboard-workflow-verification.yml"
  },
  {
    "test_item": "Real Model Smoke",
    "status": "SKIPPED",
    "evidence": "no real-model credentials were provided"
  },
  {
    "test_item": "Findings",
    "status": "PASS",
    "evidence": "[]"
  },
  {
    "test_item": "Skipped Tests",
    "status": "PASS",
    "evidence": "1 skipped in verifier inner pytest: recursive self-test guard"
  },
  {
    "test_item": "Working Tree",
    "status": "PASS",
    "evidence": "preflight working tree status"
  },
  {
    "test_item": "Final Verdict",
    "status": "PASS",
    "evidence": "computed from blocker test items"
  }
]

## 13. Verdict
- STORYBOARD_TECHNICAL_VERDICT: PASS
- STORYBOARD_QUALITY_STATUS: PENDING_USER_REVIEW
- SHOT_PROMPT_DEVELOPMENT: ALLOWED

STORYBOARD_TECHNICAL_VERDICT=PASS
STORYBOARD_QUALITY_STATUS=PENDING_USER_REVIEW
SHOT_PROMPT_DEVELOPMENT=ALLOWED
