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
      title: "뚜렷한 위험 요소가 없어요",
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
  const selectedRisk = riskView[normalizedRisk] ?? riskView.DEFAULT;

  riskCard.classList.add(selectedRisk.className);
  riskIcon.textContent = selectedRisk.icon;
  riskTitle.textContent = selectedRisk.title;
  resultSummary.textContent =
    typeof result.summary === "string" && result.summary.trim()
      ? result.summary
      : "분석 결과에 대한 설명이 없습니다.";
  mockNotice.hidden = result.mock !== true;

  renderList(result.reasons, reasonList, reasonEmpty);
  renderList(result.actions, actionList, actionEmpty);

  retryButton.addEventListener("click", () => {
    sessionStorage.removeItem(RESULT_KEY);
    window.location.assign("/");
  });
})();
