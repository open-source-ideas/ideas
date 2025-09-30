export function initToolbar(toolbar, button) {
  const closed = localStorage.getItem("ctest-toolbar-collapsed") === "true";
  if (closed) toolbar.classList.add("collapsed");
  button.addEventListener("click", () => {
    toolbar.classList.toggle("collapsed");
    localStorage.setItem(
      "ctest-toolbar-collapsed",
      toolbar.classList.contains("collapsed")
    );
  });
}
