# Quality Scorecard — KR-MOB-SMISHING v1

Automated quality metrics for the KR-MOB-SMISHING v1 dataset.
All metrics are reproducible via the included validation pipeline.

---

## Overall Summary

| Metric | Value | Status |
|---|---|---|
| Total Incidents | 100 | — |
| Total Events | ~995 | — |
| Avg Events / Incident | 10.0 | — |
| Avg Duration | 81.8 min | — |
| Validation PASS Rate | 100/100 (100%) | PASS |

---

## Case Type Distribution

| Case Type | Count | Ratio | Status |
|---|---|---|---|
| malicious | 40 | 40% | PASS |
| benign_lookalike | 31 | 31% | PASS |
| benign | 29 | 29% | PASS |
| **Coverage** | **3/3 types** | **100%** | **PASS** |

---

## Label Consistency

| Check | Expected | Actual | Status |
|---|---|---|---|
| must_fire count = malicious count | 40 | 40 | PASS |
| benign incidents with fires=true | 0 | 0 | PASS |
| ground_truth alignment | 100% | 100% | PASS |

---

## Difficulty Distribution

| Tier | Count | Ratio | Status |
|---|---|---|---|
| DT-HIGH | 48 | 48% | PASS |
| DT-MEDIUM | 42 | 42% | PASS |
| DT-LOW | 10 | 10% | PASS |
| **Coverage** | **3/3 tiers** | **100%** | **PASS** |

---

## Platform Coverage

| Platform | Appearances | Ratio | Status |
|---|---|---|---|
| Android | 57 | 50.4% | PASS |
| iOS | 56 | 49.6% | PASS |
| **Balance** | **Δ 0.8%** | — | **PASS** |

---

## Theme Coverage

| # | Theme | Count | Status |
|---|---|---|---|
| 1 | 계정 보안 경고 사칭 | 16 | PASS |
| 2 | 가족/지인 사칭 긴급 송금 | 12 | PASS |
| 3 | 채용/면접 결과 사칭 | 12 | PASS |
| 4 | 인증서 갱신/만료 사칭 | 12 | PASS |
| 5 | 통신사 요금/데이터 사칭 | 9 | PASS |
| 6 | 택배/배송 실패 사칭 | 9 | PASS |
| 7 | 결제/승인 확인 사칭 | 9 | PASS |
| 8 | 모바일 금융앱 업데이트 사칭 | 7 | PASS |
| 9 | 정부지원금/환급금 사칭 | 7 | PASS |
| 10 | 공공기관 과태료/세금 사칭 | 6 | PASS |
| | **Coverage** | **10/10** | **PASS** |

---

## Correlation Rule Benchmark

| Rule | Fires=True | Fires=False | Fire Rate | Window | Status |
|---|---|---|---|---|---|
| SMISH_REDIRECT_CHAIN | 43 | 57 | 43% | 180s | PASS |
| SENSITIVE_FORM_SEQUENCE | 39 | 61 | 39% | 600s | PASS |
| POST_LURE_FINANCIAL_RISK_SIGNAL | 30 | 70 | 30% | 900s | PASS |
| PHISH_WARNING_BYPASS | 20 | 80 | 20% | standalone | PASS |
| PLATFORM_DIVERGENCE | 7 | 93 | 7% | 900s | PASS |
| **Coverage** | — | — | — | — | **5/5 PASS** |

---

## Event Type Distribution

| Event Type | Count | Ratio | Category |
|---|---|---|---|
| background.normal_traffic | 407 | 39.3% | noise |
| dns.query | 129 | 12.5% | network |
| sms.received | 126 | 12.2% | messaging |
| http.request | 91 | 8.8% | network |
| http.redirect | 59 | 5.7% | network |
| web.risk_warning | 56 | 5.4% | browser_security |
| ios.web.behavior | 54 | 5.2% | browser_security |
| auth.step_up_challenge | 47 | 4.5% | identity |
| android.web_submission.blocked | 24 | 2.3% | endpoint |
| form.interaction | 20 | 1.9% | web_telemetry |
| bank.transfer_attempt_flagged | 17 | 1.6% | financial |
| device.compliance | 5 | 0.5% | endpoint |
| **Total** | **~995** | **100%** | **12 types** |

---

## Safety & Compliance

| Check | Requirement | Result | Status |
|---|---|---|---|
| Domain TLD | .example only (RFC 2606) | All .example | PASS |
| IP Range | TEST-NET only (RFC 5737) | All TEST-NET | PASS |
| Phone Number | Masked format only | All masked | PASS |
| Brand Name / Logo | None allowed | None found | PASS |
| [TRAINING] Watermark | All SMS must include | All included | PASS |
| Real PII | None allowed | None found | PASS |

---

## Known Limitations (v1)

| Issue | Impact | Fix Plan |
|---|---|---|
| timeline_profile naming variants (16 forms) | Filtering inconvenience | Fixed in v2 prompt |
| theme naming variants (5 cases) | Filtering inconvenience | Fixed in v2 prompt |
| DT-LOW underrepresented (10%) | Limited easy-tier training | Rebalanced in v2 |
| Max duration 930 min (1 outlier) | Cosmetic | Cap added in v2 |

---

Generated: 2026-03-01
Version: v1.0.0
Validation: Automated (QualityValidator pipeline)