import { BrowserQRCodeReader } from "@zxing/browser";

function messageForCameraError(error) {
  const name = error?.name || "";
  if (name === "NotAllowedError" || name === "SecurityError") {
    return "Acesso à câmera negado. Autorize a câmera nas configurações do navegador e tente novamente.";
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return "Nenhuma câmera foi encontrada neste aparelho.";
  }
  if (name === "NotReadableError" || name === "TrackStartError") {
    return "A câmera está sendo usada por outro aplicativo. Feche-o e tente novamente.";
  }
  if (name === "OverconstrainedError" || name === "ConstraintNotSatisfiedError") {
    return "A câmera não oferece a configuração solicitada. Tente trocar a câmera.";
  }
  return `Não foi possível iniciar a câmera${error?.message ? `: ${error.message}` : "."}`;
}

export default function qrScanner(component) {
  const { parentElement, setTriggerValue } = component;
  const root = parentElement.querySelector("[data-qr-scanner-root]");
  const video = root.querySelector("video");
  const status = root.querySelector("[data-status]");
  const viewport = root.querySelector("[data-viewport]");
  const startButton = root.querySelector("[data-start]");
  const stopButton = root.querySelector("[data-stop]");
  const switchButton = root.querySelector("[data-switch]");

  const reader = new BrowserQRCodeReader(undefined, {
    delayBetweenScanAttempts: 90,
    delayBetweenScanSuccess: 500,
  });
  let controls = null;
  let starting = false;
  let detected = false;
  let facingMode = "environment";

  const setStatus = (text, kind = "info") => {
    status.textContent = text;
    status.dataset.kind = kind;
  };

  const updateButtons = (active) => {
    startButton.hidden = active;
    stopButton.hidden = !active;
    switchButton.hidden = !active;
  };

  const stopTracks = () => {
    const stream = video.srcObject;
    if (stream && typeof stream.getTracks === "function") {
      stream.getTracks().forEach((track) => track.stop());
    }
    video.srcObject = null;
  };

  const stop = (message = "Câmera parada. Toque em Iniciar câmera para ler outro QR Code.") => {
    try {
      controls?.stop();
    } catch (_) {
      // O fluxo pode já ter sido encerrado pelo navegador.
    }
    controls = null;
    starting = false;
    stopTracks();
    viewport.hidden = true;
    updateButtons(false);
    setStatus(message);
  };

  const onResult = (result) => {
    if (!result || detected) return;
    const value = String(result.getText?.() || result.text || "").trim();
    if (!value) return;
    detected = true;
    try {
      controls?.stop();
    } catch (_) {
      // A desmontagem abaixo também encerra todas as trilhas.
    }
    stopTracks();
    viewport.hidden = true;
    updateButtons(false);
    setStatus("QR Code identificado. Carregando o processo...", "success");
    if (navigator.vibrate) navigator.vibrate(100);
    setTriggerValue("scanned", { value, nonce: Date.now() });
  };

  const start = async () => {
    if (starting || controls) return;
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setStatus("A câmera exige uma conexão HTTPS e um navegador compatível.", "error");
      return;
    }
    starting = true;
    detected = false;
    startButton.disabled = true;
    setStatus("Solicitando acesso à câmera...");
    try {
      controls = await reader.decodeFromConstraints(
        {
          audio: false,
          video: {
            facingMode: { ideal: facingMode },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
        },
        video,
        onResult,
      );
      viewport.hidden = false;
      updateButtons(true);
      setStatus("Câmera ativa: aponte para um único QR Code.", "success");
    } catch (error) {
      stopTracks();
      controls = null;
      viewport.hidden = true;
      updateButtons(false);
      setStatus(messageForCameraError(error), "error");
    } finally {
      starting = false;
      startButton.disabled = false;
    }
  };

  const switchCamera = async () => {
    const nextMode = facingMode === "environment" ? "user" : "environment";
    stop("Trocando a câmera...");
    facingMode = nextMode;
    await start();
  };

  const stopFromButton = () => stop();
  startButton.addEventListener("click", start);
  stopButton.addEventListener("click", stopFromButton);
  switchButton.addEventListener("click", switchCamera);
  updateButtons(false);
  setStatus("A imagem é processada somente neste aparelho e não é enviada ao servidor.");

  return () => {
    startButton.removeEventListener("click", start);
    stopButton.removeEventListener("click", stopFromButton);
    switchButton.removeEventListener("click", switchCamera);
    stop("");
  };
}
