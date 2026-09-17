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
    };
  },
});
const window = {
  setTimeout,
  location: { replace() {}, assign() {} },
};

const code = fs.readFileSync("src/main/resources/static/js/result.js", "utf8");
vm.runInNewContext(code, {document, sessionStorage, fetch, window, console});

setTimeout(() => {
  assert.equal(elements.get("#riskTitle").textContent, "위험 가능성이 높아요");
  assert.equal(
    elements.get("#resultSummary").textContent,
    "동적 분석에서 민감정보 입력 폼이 확인되었습니다.",
  );
  assert.equal(elements.get("#dynamicStatus").textContent, "동적 분석 1건이 완료되었습니다.");
  assert.equal(JSON.parse(stored).riskLevel, "HIGH");
  console.log("Dynamic result UI escalation passed");
}, 20);
