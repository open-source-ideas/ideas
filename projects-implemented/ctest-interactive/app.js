import { loadPreferences, savePreferences } from "./preferences.js";
import { initToolbar } from "./toolbar.js";

const textarea = document.getElementById("source-text");
const generateBtn = document.getElementById("generate");
const resetBtn = document.getElementById("reset");
const sampleBtn = document.getElementById("load-sample");
const wrapper = document.getElementById("test-wrapper");
const container = document.getElementById("test-container");
const scoreOutput = document.getElementById("score-output");
const scoreBtn = document.getElementById("check-score");
const showAnswersBtn = document.getElementById("show-answers");
const optionsPanel = document.getElementById("options-form");
const toolbar = document.getElementById("toolbar");
const toolbarToggle = document.getElementById("toggle-toolbar");
initToolbar(toolbar, toolbarToggle);

let currentGaps = [];
let preferences = loadPreferences();

function hydrateOptions() {
  optionsPanel.startSentence.value = preferences.startSentence;
  optionsPanel.skipWords.value = preferences.skipWordsShorterThan;
  optionsPanel.capitalizeHints.checked = preferences.capitalizeHints;
}

hydrateOptions();

optionsPanel.addEventListener("change", () => {
  preferences = {
    startSentence: Number(optionsPanel.startSentence.value) || 1,
    skipWordsShorterThan: Number(optionsPanel.skipWords.value) || 3,
    capitalizeHints: optionsPanel.capitalizeHints.checked,
  };
  savePreferences(preferences);
});

function loadSampleText() {
  const sample = `Learning a new language requires exposure to meaningful content. The C-Test,
created in the 1980s, is a variant of the cloze test. Typically, the second half of
words is removed to assess language proficiency. This short text demonstrates how
an interactive C-Test can provide immediate feedback while the learner practices.`;
  textarea.value = sample;
}

function resetState() {
  textarea.value = "";
  container.innerHTML = "";
  wrapper.classList.add("hidden");
  currentGaps = [];
  scoreOutput.textContent = "";
}

function generate() {
  const text = textarea.value.trim();
  if (text.length < 20) {
    alert("Please paste a text containing at least two sentences.");
    return;
  }
  const data = buildCTest(text, preferences);
  if (!data.gaps.length) {
    alert("Not enough words to create gaps. Try a longer text or adjust the settings.");
    return;
  }
  renderCTest(data);
  currentGaps = data.gaps;
  wrapper.classList.remove("hidden");
  scoreOutput.textContent = "";
}

function buildCTest(text, prefs) {
  const sentences = text.match(/[^.!?]+[.!?]*/g) || [text];
  const tokens = [];
  const gaps = [];
  let gapId = 0;

  sentences.forEach((sentence, sentenceIndex) => {
    const parts = sentence.match(/\S+|\s+/g) || [];
    parts.forEach((part) => {
      if (/^\s+$/.test(part)) {
        tokens.push({ type: "text", content: part });
        return;
      }
      const match = part.match(/^([\p{L}\p{M}]+)(.*)$/u);
      if (!match || sentenceIndex < prefs.startSentence - 1) {
        tokens.push({ type: "text", content: part });
        return;
      }
      const word = match[1];
      const trailing = match[2] || "";
      if (word.length < prefs.skipWordsShorterThan) {
        tokens.push({ type: "text", content: part });
        return;
      }
      const cut = Math.ceil(word.length / 2);
      const prefix = word.slice(0, cut);
      const missingRaw = word.slice(cut);
      const missing = prefs.capitalizeHints ? missingRaw : missingRaw.toLowerCase();
      gapId += 1;
      const gapKey = `gap-${gapId}`;
      tokens.push({
        type: "gap",
        id: gapKey,
        prefix,
        missing,
        trailing,
      });
      gaps.push({ id: gapKey, missing, prefix, revealed: 0 });
    });
  });

  return { tokens, gaps };
}

function renderCTest(data) {
  container.innerHTML = "";
  data.tokens.forEach((token) => {
    if (token.type === "text") {
      container.append(token.content);
      return;
    }
    const span = document.createElement("span");
    span.className = "gap";

    const prefixSpan = document.createElement("span");
    prefixSpan.textContent = token.prefix;
    span.append(prefixSpan);

    const input = document.createElement("input");
    input.type = "text";
    input.maxLength = token.missing.length;
    input.dataset.answer = token.missing;
    input.dataset.id = token.id;
    input.autocomplete = "off";
    input.spellcheck = false;
    input.addEventListener("input", () => checkAnswer(input));
    span.append(input);

    if (token.trailing) {
      const trailing = document.createElement("span");
      trailing.textContent = token.trailing;
      span.append(trailing);
    }

    const hintBtn = document.createElement("button");
    hintBtn.type = "button";
    hintBtn.textContent = "Hint";
    hintBtn.className = "hint-button";
    hintBtn.addEventListener("click", () => provideHint(input));
    span.append(hintBtn);

    container.append(span);
  });
}

function checkAnswer(input) {
  const expected = input.dataset.answer;
  const value = input.value.trim();
  if (!value) {
    input.classList.remove("correct", "incorrect");
    return;
  }
  if (value.localeCompare(expected, undefined, { sensitivity: "accent" }) === 0) {
    input.classList.add("correct");
    input.classList.remove("incorrect");
  } else {
    input.classList.add("incorrect");
    input.classList.remove("correct");
  }
}

function provideHint(input) {
  const gap = currentGaps.find((g) => g.id === input.dataset.id);
  if (!gap) return;
  if (gap.revealed >= gap.missing.length) return;
  gap.revealed += 1;
  input.value = gap.missing.slice(0, gap.revealed);
  checkAnswer(input);
}

function calculateScore() {
  const inputs = container.querySelectorAll("input[data-answer]");
  if (!inputs.length) {
    scoreOutput.textContent = "Generate a test first.";
    return;
  }
  let correct = 0;
  inputs.forEach((input) => {
    const expected = input.dataset.answer;
    const value = input.value.trim();
    if (value.localeCompare(expected, undefined, { sensitivity: "accent" }) === 0) {
      correct += 1;
      input.classList.add("correct");
    } else {
      input.classList.add("incorrect");
    }
  });
  scoreOutput.textContent = `Score: ${correct}/${inputs.length} (${Math.round(
    (correct / inputs.length) * 100
  )}%)`;
}

function revealAnswers() {
  const inputs = container.querySelectorAll("input[data-answer]");
  inputs.forEach((input) => {
    input.value = input.dataset.answer;
    input.classList.add("correct");
    input.classList.remove("incorrect");
  });
  scoreOutput.textContent = "Answers revealed.";
}

sampleBtn.addEventListener("click", loadSampleText);
generateBtn.addEventListener("click", generate);
resetBtn.addEventListener("click", resetState);
scoreBtn.addEventListener("click", calculateScore);
showAnswersBtn.addEventListener("click", revealAnswers);
