// Local time is intentionally used; this wallpaper never contacts a service.
function roomPhase(hour) {
  if (hour >= 7 && hour < 17) return "day";
  if (hour >= 17 && hour < 21) return "dusk";
  if (hour >= 6 && hour < 7) return "dawn";
  return "night";
}

function initRoom() {
  const clock = document.getElementById("clockText");
  let timer;

  function updateTime() {
    const now = new Date();
    document.body.dataset.phase = roomPhase(now.getHours());
    clock.textContent = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    clock.dateTime = clock.textContent;
  }

  function syncVisibility() {
    clearInterval(timer);
    if (!document.hidden) {
      updateTime();
      timer = setInterval(updateTime, 60000);
    }
  }

  document.addEventListener("visibilitychange", syncVisibility);
  syncVisibility();
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", initRoom);
}
if (typeof module !== "undefined") module.exports = { roomPhase };
