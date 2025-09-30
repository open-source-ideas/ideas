export function loadPreferences() {
  const defaults = {
    startSentence: 1,
    skipWordsShorterThan: 3,
    capitalizeHints: true,
  };
  try {
    const stored = localStorage.getItem("ctest-preferences");
    if (!stored) return defaults;
    return { ...defaults, ...JSON.parse(stored) };
  } catch (err) {
    console.warn("Failed to load preferences", err);
    return defaults;
  }
}

export function savePreferences(prefs) {
  try {
    localStorage.setItem("ctest-preferences", JSON.stringify(prefs));
  } catch (err) {
    console.warn("Failed to save preferences", err);
  }
}
