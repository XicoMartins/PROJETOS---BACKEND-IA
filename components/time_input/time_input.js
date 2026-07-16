function onlyDigits(value) {
  return String(value ?? "").replace(/\D/g, "").slice(0, 4);
}

function formatDigits(value) {
  const digits = onlyDigits(value);
  if (digits.length < 2) return digits;
  return `${digits.slice(0, 2)}:${digits.slice(2)}`;
}

export default function timeInput(component) {
  const { data, parentElement, setTriggerValue } = component;
  const root = parentElement.querySelector("[data-hhmm-root]");
  const label = root.querySelector("[data-label]");
  const input = root.querySelector("[data-input]");
  const inputId = `hhmm-${String(data.key || "field").replace(/[^a-zA-Z0-9_-]/g, "-")}`;

  label.textContent = data.label;
  label.htmlFor = inputId;
  input.id = inputId;
  input.setAttribute("aria-label", data.label);
  input.value = formatDigits(data.value);
  let lastCommitted = onlyDigits(input.value);

  const onInput = () => {
    input.value = formatDigits(input.value);
    input.setSelectionRange(input.value.length, input.value.length);
  };

  const commit = () => {
    const digits = onlyDigits(input.value);
    if (digits === lastCommitted) return;
    lastCommitted = digits;
    setTriggerValue("changed", {
      value: digits,
      nonce: Date.now(),
    });
  };

  const onKeyDown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      commit();
      input.blur();
      return;
    }
    if (
      event.key === "Backspace" &&
      input.value.endsWith(":") &&
      input.selectionStart === input.value.length &&
      input.selectionEnd === input.value.length
    ) {
      event.preventDefault();
      input.value = formatDigits(onlyDigits(input.value).slice(0, -1));
    }
  };

  const onFocus = () => input.select();
  input.addEventListener("input", onInput);
  input.addEventListener("keydown", onKeyDown);
  input.addEventListener("blur", commit);
  input.addEventListener("focus", onFocus);

  return () => {
    input.removeEventListener("input", onInput);
    input.removeEventListener("keydown", onKeyDown);
    input.removeEventListener("blur", commit);
    input.removeEventListener("focus", onFocus);
  };
}
