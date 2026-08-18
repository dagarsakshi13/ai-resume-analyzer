const fileInput = document.getElementById("resume");
const fileName = document.getElementById("fileName");
const analyzeBtn = document.getElementById("analyzeBtn");

fileInput.addEventListener("change", function () {
    if (fileInput.files.length > 0) {
        fileName.textContent = fileInput.files[0].name;
        analyzeBtn.disabled = false;
    } else {
        fileName.textContent = "No file selected";
        analyzeBtn.disabled = true;
    }
});