function onlyDigits(value) {
  return String(value ?? "").replace(/\D/g, "").slice(0, 4);
}

function previewFor(value) {
  if (value.length !== 4) return "Digite 4 números. Ex.: 0830";
  const hour = Number(value.slice(0, 2));
  const minute = Number(value.slice(2, 4));
  if (hour > 23 || minute > 59) return "Horário inválido";
  return `${value.slice(0, 2)}:${value.slice(2, 4)}`;
}

export default function timeInput(component) {
  const { data, parentElement, setTriggerValue } = component;
  const root = parentElement.querySelector("[data-hhmm-root]");
  const label = root.querySelector("[data-label]");
  const input = root.querySelector("[data-input]");
  const preview = root.querySelector("[data-preview]");
  const inputId = `hhmm-${String(data.key || "field").replace(/[^a-zA-Z0-9_-]/g, "-")}`;

  label.textContent = `${data.label} (HHMM)`;
  label.htmlFor = inputId;
  input.id = inputId;
  input.setAttribute("aria-label", `${data.label} (HHMM)`);
  input.value = onlyDigits(data.value);
  let lastCommitted = input.value;

  const updatePreview = () => {
    const message = previewFor(input.value);
    preview.textContent = message;
    preview.dataset.invalid = message === "Horário inválido" ? "true" : "false";
  };

  const onInput = () => {
    const sanitized = onlyDigits(input.value);
    if (input.value !== sanitized) input.value = sanitized;
    updatePreview();
  };

  const commit = () => {
    if (input.value === lastCommitted) return;
    lastCommitted = input.value;
    setTriggerValue("changed", {
      value: input.value,
      nonce: Date.now(),
    });
  };

  const onKeyDown = (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    commit();
    input.blur();
  };

  const onFocus = () => input.select();
  input.addEventListener("input", onInput);
  input.addEventListener("keydown", onKeyDown);
  input.addEventListener("blur", commit);
  input.addEventListener("focus", onFocus);
  updatePreview();

  return () => {
    input.removeEventListener("input", onInput);
    input.removeEventListener("keydown", onKeyDown);
    input.removeEventListener("blur", commit);
    input.removeEventListener("focus", onFocus);
  };
}
