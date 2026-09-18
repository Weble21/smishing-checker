const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const elements = new Map();
function element() {
  return {
    hidden: false,
    children: [],
    classList: { add() {}, remove() {} },
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
    addEventListener() {},
  };
}
const document = {
  querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, element());
    return elements.get(selector);
  },
  createElement: element,
};
let stored = JSON.stringify({
  riskLevel: "MEDIUM",
  summary: "정적 분석 결과",
  reasons: ["미확인 URL"],
  actions: ["링크를 누르지 마세요."],
  analysisStatus: "SUCCESS",
  textRiskScore: 0.8,
  dynamicAnalyses: [{jobId: "a".repeat(32), status: "QUEUED"}],
});
const sessionStorage = {
  getItem() { return stored; },
  setItem(key, value) { stored = value; },
  removeItem() {},
};
const fetch = async () => ({
  ok: true,
  async json() {
    return {
      jobId: "a".repeat(32), status: "COMPLETED",
      verdict: "SUSPICIOUS", riskLevel: "HIGH",
      summary: "동적 분석에서 민감정보 입력 폼이 확인되었습니다.",
      reasons: ["비밀번호 입력 항목이 있습니다."],
      evidence: ["최종 URL: https://example.com/login", "폼 POST: https://example.com/submit (입력 유형: password)"],
    };
  },
});
const window = {
  setTimeout,
  location: { replace() {}, assign() {} },
};

const code = fs.readFileSync("src/main/resources/static/js/result.js", "utf8");
vm.runInNewContext(code, {document, sessionStorage, fetch, window, console});
assert.equal(elements.has("#textRiskScore"), false);

setTimeout(() => {
  assert.equal(elements.get("#riskTitle").textContent, "위험 가능성이 높아요");
  assert.equal(
    elements.get("#resultSummary").textContent,
    "동적 분석에서 민감정보 입력 폼이 확인되었습니다.",
  );
  assert.equal(elements.get("#dynamicStatus").textContent, "동적 분석 완료 1건 · 시간 초과 0건 · 실패 0건 · 만료 0건");
  assert.deepEqual(elements.get("#dynamicReasonList").children.map((item) => item.textContent), [
    "비밀번호 입력 항목이 있습니다.",
    "최종 URL: https://example.com/login",
    "폼 POST: https://example.com/submit (입력 유형: password)",
  ]);
  assert.equal(JSON.parse(stored).riskLevel, "HIGH");
  console.log("Dynamic result UI escalation passed");

  elements.clear();
  stored = JSON.stringify({
    riskLevel: "LOW", summary: "Static low risk", reasons: [], actions: [],
    analysisStatus: "SUCCESS", textRiskScore: 0.1,
    dynamicAnalyses: [{jobId: "b".repeat(32), status: "QUEUED"}],
  });
  const failedFetch = async () => ({
    ok: true,
    async json() {
      return {
        jobId: "b".repeat(32), status: "FAILED", verdict: "INCONCLUSIVE",
        riskLevel: null, reasons: ["Analysis failed"], evidence: [],
      };
    },
  });
  vm.runInNewContext(code, {document, sessionStorage, fetch: failedFetch, window, console});
  assert.equal(elements.has("#textRiskScore"), false);
  setTimeout(() => {
    assert.equal(JSON.parse(stored).riskLevel, "REVIEW_REQUIRED");
    assert.equal(elements.get("#riskTitle").textContent, "확인이 필요해요");
    assert.ok(elements.get("#dynamicStatus").textContent.includes("실패 1건"));
    console.log("Dynamic result UI failure remains inconclusive");

    elements.clear();
    stored = JSON.stringify({
      riskLevel: "LOW", summary: "Static low risk", reasons: [], actions: [],
      analysisStatus: "SUCCESS", textRiskScore: 0.1,
      dynamicAnalyses: [{jobId: "c".repeat(32), status: "QUEUED"}],
    });
    const expiredFetch = async () => ({status: 404, ok: false});
    vm.runInNewContext(code, {document, sessionStorage, fetch: expiredFetch, window, console});
    setTimeout(() => {
      const result = JSON.parse(stored);
      assert.equal(result.riskLevel, "REVIEW_REQUIRED");
      assert.equal(result.dynamicAnalyses[0].status, "EXPIRED");
      assert.ok(elements.get("#dynamicStatus").textContent.includes("만료 1건"));
      console.log("Dynamic result UI expiry remains inconclusive");
    }, 20);
  }, 20);
}, 20);
