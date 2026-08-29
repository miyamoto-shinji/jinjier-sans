const root = document.documentElement;
const weightInput = document.querySelector("#weight");
const weightValue = document.querySelector("#value");
const sizeInput = document.querySelector("#font-size");
const sizeValue = document.querySelector("#size-value");
const testerText = document.querySelector("#tester-text");
const copyStatus = document.querySelector("#copy-status");
const weightButtons = [...document.querySelectorAll("[data-weight]")];
const presetButtons = [...document.querySelectorAll("[data-preset]")];
const copyButtons = [...document.querySelectorAll("[data-copy-target]")];

const samples = {
  jp: "「ひと」の可能性のすべてが見える世界へ",
  en: "Friendly, warm & playful — jinjer sans",
  num: "09:00–18:00\n¥412,345 / 12.5% / JNJR-2026",
  ui: "勤怠管理　給与明細　社員番号\nPeople Directory / Payroll",
};

function updatePressedState(buttons, isActive) {
  buttons.forEach((button) => {
    button.setAttribute("aria-pressed", String(isActive(button)));
  });
}

function setWeight(nextWeight) {
  const weight = String(nextWeight);
  weightInput.value = weight;
  weightValue.value = weight;
  root.style.setProperty("--demo-weight", weight);

  updatePressedState(weightButtons, (button) => button.dataset.weight === weight);
}

function setSize(nextSize) {
  const size = String(nextSize);
  sizeInput.value = size;
  sizeValue.value = `${size}px`;
  root.style.setProperty("--tester-size", `${size}px`);
}

weightInput.addEventListener("input", () => setWeight(weightInput.value));
sizeInput.addEventListener("input", () => setSize(sizeInput.value));

weightButtons.forEach((button) => {
  button.addEventListener("click", () => setWeight(button.dataset.weight));
});

presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    testerText.innerText = samples[button.dataset.preset];
    updatePressedState(presetButtons, (item) => item === button);
  });
});

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();

  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("Copy command was rejected");
}

copyButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    const original = button.textContent;

    try {
      if (!target) throw new Error("Copy target was not found");
      await copyText(target.innerText);
      button.textContent = "Copied";
      copyStatus.textContent = "コードをコピーしました";
    } catch {
      button.textContent = "Select & copy";
      copyStatus.textContent = "コピーできませんでした。コードを選択してコピーしてください";
    }

    window.setTimeout(() => {
      button.textContent = original;
    }, 1600);
  });
});

setWeight(weightInput.value);
setSize(window.matchMedia("(max-width: 640px)").matches ? 58 : sizeInput.value);
