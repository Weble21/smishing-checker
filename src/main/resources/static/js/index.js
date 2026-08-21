(() => {
    'use strict';

    const MAX_FILE_SIZE = 10 * 1024 * 1024;
    const ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/gif']);
    const input = document.querySelector('#imageInput');
    const selectButton = document.querySelector('#selectButton');
    const analyzeButton = document.querySelector('#analyzeButton');
    const uploadCard = document.querySelector('#uploadCard');
    const emptyState = document.querySelector('#emptyState');
    const previewState = document.querySelector('#previewState');
    const previewImage = document.querySelector('#imagePreview');
    const fileName = document.querySelector('#fileName');
    const fileError = document.querySelector('#fileError');
    let previewUrl;
    let selectedFile;

    const clearError = () => {
        fileError.textContent = '';
        input.removeAttribute('aria-invalid');
    };

    const showError = (message) => {
        fileError.textContent = message;
        input.setAttribute('aria-invalid', 'true');
        input.value = '';
    };

    const validateFile = (file) => {
        if (!ALLOWED_TYPES.has(file.type)) {
            return 'JPG, PNG, WEBP, GIF \ud615\uc2dd\uc758 \uc774\ubbf8\uc9c0\ub9cc \uc120\ud0dd\ud560 \uc218 \uc788\uc5b4\uc694.';
        }
        if (file.size > MAX_FILE_SIZE) {
            return '\ud30c\uc77c \ud06c\uae30\ub294 10MB \uc774\ud558\uc5ec\uc57c \ud574\uc694.';
        }
        return '';
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
        selectButton.textContent = '\ub2e4\ub978 \uc0ac\uc9c4 \uc120\ud0dd\ud558\uae30';
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

    selectButton.addEventListener('click', () => input.click());
    analyzeButton.addEventListener('click', () => {
        if (selectedFile) window.location.href = '/result';
    });
    input.addEventListener('change', () => handleFile(input.files[0]));

    ['dragenter', 'dragover'].forEach((eventName) => {
        uploadCard.addEventListener(eventName, (event) => {
            event.preventDefault();
            uploadCard.classList.add('is-dragging');
        });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
        uploadCard.addEventListener(eventName, (event) => {
            event.preventDefault();
            uploadCard.classList.remove('is-dragging');
        });
    });

    uploadCard.addEventListener('drop', (event) => handleFile(event.dataTransfer.files[0]));
    window.addEventListener('beforeunload', () => {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
    });
})();
