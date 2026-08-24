(() => {
  "use strict";

  const MAX_FILE_SIZE = 10 * 1024 * 1024;
  const ALLOWED_TYPES = new Set([
    "image/jpeg",
    "image/png",
  ]);
  const input = document.querySelector("#imageInput");
  const selectButton = document.querySelector("#selectButton");
  const analyzeButton = document.querySelector("#analyzeButton");
  const uploadCard = document.querySelector("#uploadCard");
  const emptyState = document.querySelector("#emptyState");
  const previewState = document.querySelector("#previewState");
  const previewImage = document.querySelector("#imagePreview");
  const fileName = document.querySelector("#fileName");
  const fileError = document.querySelector("#fileError");

  let previewUrl;
  let selectedFile = null;

  const clearError = () => {
    fileError.textContent = "";
    input.removeAttribute("aria-invalid");
  };

  const showError = (message) => {
    fileError.textContent = message;
    input.setAttribute("aria-invalid", "true");
    input.value = "";
  };

  const validateFile = (file) => {
    if (!ALLOWED_TYPES.has(file.type)) {
      return "JPG, PNG 형식의 이미지만 선택할 수 있어요.";
    }
    if (file.size > MAX_FILE_SIZE) {
      return "파일 크기는 10MB 이하여야 해요.";
    }
    return "";
  };

  const showPreview = (file) => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    selectedFile = file;
    previewImage.src = previewUrl;
    fileName.textContent = file.name;
    emptyState.hidden = true;
    previewState.hidden = false;
    analyzeButton.hidden = false;
    selectButton.textContent = "다른 사진 선택하기";
  };

  const handleFile = (file) => {
    clearError();
    if (!file) return;

    const error = validateFile(file);
    if (error) {
      showError(error);
      return;
    }
    showPreview(file);
  };

  selectButton.addEventListener("click", () => input.click());
  input.addEventListener("change", () => handleFile(input.files[0]));

  ["dragenter", "dragover"].forEach((eventName) => {
    uploadCard.addEventListener(eventName, (event) => {
      event.preventDefault();
      uploadCard.classList.add("is-dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    uploadCard.addEventListener(eventName, (event) => {
      event.preventDefault();
      uploadCard.classList.remove("is-dragging");
    });
  });

  uploadCard.addEventListener("drop", (event) => {
    handleFile(event.dataTransfer.files[0]);
  });

  analyzeButton.addEventListener("click", async () => {
    if (!selectedFile) {
      showError("사진을 먼저 선택해주세요.");
      return;
    }

    clearError();
    const formData = new FormData();
    formData.append("image", selectedFile);
    analyzeButton.disabled = true;
    analyzeButton.textContent = "확인하고 있어요...";

    try {
      const response = await fetch("/api/v1/messages/analyze", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message ?? "사진을 분석하지 못했어요.");
      }

      sessionStorage.setItem("analysisResult", JSON.stringify(data));
      window.location.assign("/result");
    } catch (error) {
      showError(error.message || "사진을 분석하지 못했어요.");
    } finally {
      analyzeButton.disabled = false;
      analyzeButton.textContent = "이 사진 분석하기";
    }
  });

  window.addEventListener("beforeunload", () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  });
})();
