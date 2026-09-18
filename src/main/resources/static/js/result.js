(() => {
  "use strict";

  const RESULT_KEY = "analysisResult";
  const riskCard = document.querySelector("#riskCard");
  const riskIcon = document.querySelector("#riskIcon");
  const riskTitle = document.querySelector("#riskTitle");
  const resultSummary = document.querySelector("#resultSummary");
  const reasonList = document.querySelector("#reasonList");
  const reasonEmpty = document.querySelector("#reasonEmpty");
  const actionList = document.querySelector("#actionList");
  const actionEmpty = document.querySelector("#actionEmpty");
  const mockNotice = document.querySelector("#mockNotice");
  const retryButton = document.querySelector("#retryButton");
  const dynamicSection = document.querySelector("#dynamicSection");
  const dynamicStatus = document.querySelector("#dynamicStatus");
  const dynamicReasonList = document.querySelector("#dynamicReasonList");

  const riskView = {
    HIGH: {
      icon: "🔴",
      title: "위험 가능성이 높아요",
      className: "risk-card--high",
    },
    MEDIUM: {
      icon: "🟡",
      title: "주의가 필요해요",
      className: "risk-card--medium",
    },
    LOW: {
      icon: "🟢",
      title: "URL 기준 안전으로 분류했어요",
      className: "risk-card--low",
    },
    REVIEW_REQUIRED: {
      icon: "🔵",
      title: "확인이 필요해요",
      className: "risk-card--unknown",
    },
    DEFAULT: {
      icon: "🔵",
      title: "판단 결과를 확인해주세요",
      className: "risk-card--unknown",
    },
  };

  const redirectHome = () => {
    window.location.replace("/");
  };

  const readResult = () => {
    const storedResult = sessionStorage.getItem(RESULT_KEY);
    if (!storedResult) return null;

    try {
      const parsedResult = JSON.parse(storedResult);
      return parsedResult && typeof parsedResult === "object"
        ? parsedResult
        : null;
    } catch {
      sessionStorage.removeItem(RESULT_KEY);
      return null;
    }
  };

  const renderList = (values, listElement, emptyElement) => {
    listElement.replaceChildren();
    const items = Array.isArray(values)
      ? values.filter((value) => typeof value === "string" && value.trim())
      : [];

    items.forEach((value) => {
      const item = document.createElement("li");
      item.textContent = value;
      listElement.appendChild(item);
    });

    emptyElement.hidden = items.length > 0;
  };

  const result = readResult();
  if (!result) {
    redirectHome();
    return;
  }

  const normalizedRisk =
    typeof result.riskLevel === "string"
      ? result.riskLevel.toUpperCase()
      : "";
  const renderRisk = (risk) => {
    const view = riskView[risk] ?? riskView.DEFAULT;
    Object.values(riskView).forEach(({ className }) => riskCard.classList.remove(className));
    riskCard.classList.add(view.className);
    riskIcon.textContent = view.icon;
    riskTitle.textContent = view.title;
  };
  renderRisk(normalizedRisk);
  resultSummary.textContent =
    typeof result.summary === "string" && result.summary.trim()
      ? result.summary
      : "분석 결과에 대한 설명이 없습니다.";
  mockNotice.hidden = result.mock !== true;

  renderList(result.reasons, reasonList, reasonEmpty);
  renderList(result.actions, actionList, actionEmpty);

  const jobs = Array.isArray(result.dynamicAnalyses)
    ? result.dynamicAnalyses.filter((job) =>
        job && typeof job.jobId === "string" && /^[0-9a-f]{32}$/.test(job.jobId))
    : [];
  if (jobs.length > 0) {
    dynamicSection.hidden = false;
    const completedJobs = new Set();
    const jobStates = new Map(jobs.map((job) => [job.jobId, job]));
    const dynamicReasons = [];
    let attempts = 0;

    const poll = async () => {
      attempts += 1;
      const pending = jobs.filter((job) => !completedJobs.has(job.jobId));
      const responses = await Promise.allSettled(pending.map(async (job) => {
        const response = await fetch(`/api/v1/messages/dynamic/${job.jobId}`);
        if (response.status === 404) {
          return {
            jobId: job.jobId, status: "EXPIRED", verdict: "INCONCLUSIVE",
            riskLevel: null,
            summary: "동적 분석 결과가 만료되었습니다. 다시 검사해주세요.",
            reasons: ["동적 분석 결과를 더 이상 조회할 수 없습니다."],
            evidence: [],
          };
        }
        if (!response.ok) throw new Error("동적 분석 상태를 조회하지 못했습니다.");
        return response.json();
      }));

      responses.forEach((response, index) => {
        const original = pending[index];
        if (response.status !== "fulfilled") return;
        const job = response.value;
        jobStates.set(original.jobId, job);
        if (["COMPLETED", "TIMED_OUT", "FAILED", "EXPIRED"].includes(job.status)) {
          completedJobs.add(original.jobId);
        }
        if (job.riskLevel === "HIGH") {
          result.riskLevel = "HIGH";
          renderRisk("HIGH");
          if (typeof job.summary === "string" && job.summary.trim()) {
            result.summary = job.summary;
            resultSummary.textContent = job.summary;
          }
        } else if (["TIMED_OUT", "FAILED", "EXPIRED"].includes(job.status) && result.riskLevel === "LOW") {
          result.riskLevel = "REVIEW_REQUIRED";
          renderRisk("REVIEW_REQUIRED");
          const detail = typeof job.summary === "string" && job.summary.trim()
            ? job.summary.trim()
            : "동적 분석을 완료하지 못했습니다.";
          result.summary = `${detail} 링크를 안전하다고 판단할 수 없어 직접 확인이 필요합니다.`;
          resultSummary.textContent = result.summary;
        }
        for (const values of [job.reasons, job.evidence]) {
          if (!Array.isArray(values)) continue;
          values.forEach((reason) => {
            if (typeof reason === "string" && reason.trim() && !dynamicReasons.includes(reason)) {
              dynamicReasons.push(reason);
            }
          });
        }
      });

      renderList(dynamicReasons, dynamicReasonList, { hidden: true });
      result.dynamicAnalyses = jobs.map((original) => jobStates.get(original.jobId));
      sessionStorage.setItem(RESULT_KEY, JSON.stringify(result));

      const done = completedJobs.size;
      if (done === jobs.length) {
        const states = [...jobStates.values()];
        const completed = states.filter((job) => job.status === "COMPLETED").length;
        const timedOut = states.filter((job) => job.status === "TIMED_OUT").length;
        const failed = states.filter((job) => job.status === "FAILED").length;
        const expired = states.filter((job) => job.status === "EXPIRED").length;
        dynamicStatus.textContent = `동적 분석 완료 ${completed}건 · 시간 초과 ${timedOut}건 · 실패 ${failed}건 · 만료 ${expired}건`;
      } else {
        dynamicStatus.textContent = `동적 분석 중입니다. (${done}/${jobs.length})`;
      }
      if (done < jobs.length && attempts < 20) {
        window.setTimeout(poll, 2000);
      } else if (done < jobs.length) {
        dynamicStatus.textContent = "동적 분석이 계속 진행 중입니다. 잠시 후 결과를 다시 확인해주세요.";
      }
    };
    dynamicStatus.textContent = `동적 분석 중입니다. (0/${jobs.length})`;
    poll();
  }

  retryButton.addEventListener("click", () => {
    sessionStorage.removeItem(RESULT_KEY);
    window.location.assign("/");
  });
})();
