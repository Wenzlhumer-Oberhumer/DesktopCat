// Desktop Cat Cozy Room — Dynamischer Tag/Nacht- und Uhrenzyklus
function initRoom() {
  const sky = document.getElementById("sky");
  const sun = document.getElementById("sun");
  const moon = document.getElementById("moon");
  const starsContainer = document.getElementById("stars");
  const clockText = document.getElementById("clockText");

  // Sterne erzeugen
  for (let i = 0; i < 45; i++) {
    const star = document.createElement("div");
    star.className = "star";
    star.style.left = Math.random() * 100 + "%";
    star.style.top = Math.random() * 65 + "%";
    const sz = Math.random() * 2.5 + 1.2;
    star.style.width = sz + "px";
    star.style.height = sz + "px";
    star.style.animationDelay = Math.random() * 3 + "s";
    starsContainer.appendChild(star);
  }

  function updateTime() {
    const now = new Date();
    const hours = now.getHours();
    const mins = now.getMinutes();
    const timeStr = String(hours).padStart(2, "0") + ":" + String(mins).padStart(2, "0");
    if (clockText) clockText.textContent = timeStr;

    // Tag / Nacht Phasen
    // 06:00 - 17:00 -> Tag
    // 17:00 - 21:00 -> Dämmerung / Golden Hour
    // 21:00 - 06:00 -> Gemütliche Nacht
    sky.classList.remove("sky-day", "sky-dusk", "sky-night");

    if (hours >= 6 && hours < 17) {
      sky.classList.add("sky-day");
      sun.style.opacity = "1";
      sun.style.transform = "translateY(0px)";
      moon.style.opacity = "0";
      moon.style.transform = "translateY(50px)";
      starsContainer.style.opacity = "0";
    } else if (hours >= 17 && hours < 21) {
      sky.classList.add("sky-dusk");
      sun.style.opacity = "0.7";
      sun.style.transform = "translateY(80px)";
      moon.style.opacity = "0.4";
      moon.style.transform = "translateY(20px)";
      starsContainer.style.opacity = "0.4";
    } else {
      sky.classList.add("sky-night");
      sun.style.opacity = "0";
      sun.style.transform = "translateY(120px)";
      moon.style.opacity = "1";
      moon.style.transform = "translateY(0px)";
      starsContainer.style.opacity = "1";
    }
  }

  updateTime();
  setInterval(updateTime, 10000); // Alle 10s prüfen
}

document.addEventListener("DOMContentLoaded", initRoom);
