# Changelog

All notable changes to KR-MOB-SMISHING will be documented in this file.

---

## [v1.0.0] — 2026-03-01

### Initial Release

**Dataset**
- 100 synthetic mobile smishing incidents (JSON, 1 file per incident)
- 3 case types: malicious (40), benign_lookalike (31), benign (29)
- 10 Korean smishing themes
- 12 event types with MITRE ATT&CK for Mobile mapping
- 5 SIEM correlation rules with pre-verified fire/no-fire labels
- Dual platform: Android (50.4%) / iOS (49.6%)
- 3 difficulty tiers: DT-HIGH (48%), DT-MEDIUM (42%), DT-LOW (10%)

**Quality**
- Validation PASS rate: 100% (100/100)
- Label consistency: 100% (must_fire count = malicious count)
- Safety compliance: all domains .example, all IPs TEST-NET, all phones masked

**Safety**
- All SMS contain [TRAINING] watermark
- Zero real-world brand names, logos, domains, IPs, or phone numbers

---

## [v2.0.0] — Planned

### Planned Improvements
- timeline_profile field standardization (3 fixed values only)
- theme field normalization (seed-original names only)
- Expanded to 200+ incidents
- SIEM Detection Benchmark (Elastic Security TPR/FPR metrics)
- Additional smishing themes
- Enhanced difficulty tier balance (more DT-LOW cases)