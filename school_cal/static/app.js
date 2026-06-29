"use strict";

const state = {
  currentDate: new Date(),
  editingEvent: null,
  events: [],
  form: {
    date: "",
    period: "1교시",
    type: "수행평가",
    title: "",
  },
  meta: {
    periods: [],
    event_types: [],
    today_rice_url: "/today-rice",
  },
};

const nodes = {
  calendarGrid: document.querySelector("#calendarGrid"),
  closeModal: document.querySelector("#closeModal"),
  deleteButton: document.querySelector("#deleteButton"),
  eventForm: document.querySelector("#eventForm"),
  eventModal: document.querySelector("#eventModal"),
  eventTitle: document.querySelector("#eventTitle"),
  legend: document.querySelector("#legend"),
  mealLink: document.querySelector("#mealLink"),
  modalTitle: document.querySelector("#modalTitle"),
  monthLabel: document.querySelector("#monthLabel"),
  nextMonth: document.querySelector("#nextMonth"),
  periodOptions: document.querySelector("#periodOptions"),
  prevMonth: document.querySelector("#prevMonth"),
  quickAddButton: document.querySelector("#quickAddButton"),
  selectedDateLabel: document.querySelector("#selectedDateLabel"),
  toast: document.querySelector("#toast"),
  typeOptions: document.querySelector("#typeOptions"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = "요청을 처리하지 못했습니다.";
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      // Keep the default message when the response body is not JSON.
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function formatDate(year, monthIndex, day) {
  const month = String(monthIndex + 1).padStart(2, "0");
  const date = String(day).padStart(2, "0");
  return `${year}-${month}-${date}`;
}

function formatDateLabel(dateText) {
  const [year, month, day] = dateText.split("-");
  return `${year}년 ${Number(month)}월 ${Number(day)}일`;
}

function getMonthRange(date) {
  const year = date.getFullYear();
  const month = date.getMonth();
  const endDay = new Date(year, month + 1, 0).getDate();
  return {
    start: formatDate(year, month, 1),
    end: formatDate(year, month, endDay),
  };
}

function toneForType(typeValue) {
  const match = state.meta.event_types.find((item) => item.value === typeValue);
  return match ? match.tone : "violet";
}

function eventsForDate(dateText) {
  return state.events
    .filter((event) => event.date === dateText)
    .sort((a, b) => {
      const periodDiff = state.meta.periods.indexOf(a.period) - state.meta.periods.indexOf(b.period);
      return periodDiff || a.title.localeCompare(b.title, "ko");
    });
}

function renderCalendar() {
  const year = state.currentDate.getFullYear();
  const month = state.currentDate.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDay = new Date(year, month, 1).getDay();
  const today = new Date();
  const todayText = formatDate(today.getFullYear(), today.getMonth(), today.getDate());

  nodes.monthLabel.textContent = `${year}.${String(month + 1).padStart(2, "0")}`;
  nodes.calendarGrid.replaceChildren();

  for (let index = 0; index < firstDay; index += 1) {
    const blankCell = document.createElement("div");
    blankCell.className = "blank-cell";
    nodes.calendarGrid.append(blankCell);
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const dateText = formatDate(year, month, day);
    const cell = document.createElement("div");
    cell.className = dateText === todayText ? "day-cell today" : "day-cell";
    cell.setAttribute("role", "button");
    cell.tabIndex = 0;
    cell.setAttribute("aria-label", `${formatDateLabel(dateText)} 일정 추가`);
    cell.addEventListener("click", () => openAddModal(dateText));
    cell.addEventListener("keydown", (eventObject) => {
      if (eventObject.key === "Enter" || eventObject.key === " ") {
        eventObject.preventDefault();
        openAddModal(dateText);
      }
    });

    const head = document.createElement("div");
    head.className = "day-head";

    const number = document.createElement("span");
    number.className = "day-number";
    number.textContent = String(day);

    const add = document.createElement("span");
    add.className = "add-day";
    add.setAttribute("aria-hidden", "true");
    add.textContent = "+";

    head.append(number, add);
    cell.append(head);

    const list = document.createElement("div");
    list.className = "event-list";
    eventsForDate(dateText).forEach((event) => list.append(renderEventChip(event)));
    cell.append(list);

    nodes.calendarGrid.append(cell);
  }
}

function renderEventChip(event) {
  const chip = document.createElement("button");
  chip.type = "button";
  chip.className = `event-chip tone-${toneForType(event.type)}`;
  chip.addEventListener("click", (eventObject) => {
    eventObject.stopPropagation();
    openEditModal(event);
  });

  const period = document.createElement("span");
  period.className = "event-period";
  period.textContent = event.period;

  const title = document.createElement("span");
  title.className = "event-title";
  title.textContent = event.title;

  chip.append(period, title);
  return chip;
}

function renderMetaControls() {
  nodes.mealLink.href = state.meta.today_rice_url;
  nodes.legend.replaceChildren();
  nodes.typeOptions.replaceChildren();
  nodes.periodOptions.replaceChildren();

  state.meta.event_types.forEach((type) => {
    const legendItem = document.createElement("span");
    legendItem.className = "legend-item";

    const swatch = document.createElement("span");
    swatch.className = `legend-swatch tone-${type.tone}`;
    swatch.setAttribute("aria-hidden", "true");

    const label = document.createElement("span");
    label.textContent = type.label;

    legendItem.append(swatch, label);
    nodes.legend.append(legendItem);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "option-button";
    button.dataset.value = type.value;
    button.textContent = type.label;
    button.addEventListener("click", () => {
      state.form.type = type.value;
      syncFormControls();
    });
    nodes.typeOptions.append(button);
  });

  state.meta.periods.forEach((period) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "option-button";
    button.dataset.value = period;
    button.textContent = period;
    button.addEventListener("click", () => {
      state.form.period = period;
      syncFormControls();
    });
    nodes.periodOptions.append(button);
  });
}

function syncFormControls() {
  nodes.typeOptions.querySelectorAll(".option-button").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.value === state.form.type));
  });

  nodes.periodOptions.querySelectorAll(".option-button").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.value === state.form.period));
  });
}

function openAddModal(dateText) {
  state.editingEvent = null;
  state.form = {
    date: dateText,
    period: state.meta.periods.includes("1교시") ? "1교시" : state.meta.periods[0],
    type: state.meta.event_types[0].value,
    title: "",
  };
  nodes.modalTitle.textContent = "새 일정 추가";
  nodes.deleteButton.hidden = true;
  showModal();
}

function openEditModal(event) {
  state.editingEvent = event;
  state.form = {
    date: event.date,
    period: event.period,
    type: event.type,
    title: event.title,
  };
  nodes.modalTitle.textContent = "일정 수정";
  nodes.deleteButton.hidden = false;
  showModal();
}

function showModal() {
  nodes.selectedDateLabel.textContent = formatDateLabel(state.form.date);
  nodes.eventTitle.value = state.form.title;
  syncFormControls();
  nodes.eventModal.hidden = false;
  window.setTimeout(() => nodes.eventTitle.focus(), 0);
}

function closeModal() {
  nodes.eventModal.hidden = true;
}

async function loadEvents() {
  const range = getMonthRange(state.currentDate);
  state.events = await api(`/api/events?start=${range.start}&end=${range.end}`);
  renderCalendar();
}

async function saveEvent(eventObject) {
  eventObject.preventDefault();
  const title = nodes.eventTitle.value.trim();
  if (!title) {
    showToast("상세 내용을 입력하세요.");
    return;
  }

  const payload = {
    date: state.form.date,
    period: state.form.period,
    type: state.form.type,
    title,
  };

  try {
    if (state.editingEvent) {
      await api(`/api/events/${state.editingEvent.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      showToast("일정을 수정했습니다.");
    } else {
      await api("/api/events", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showToast("일정을 추가했습니다.");
    }
    closeModal();
    await loadEvents();
  } catch (error) {
    showToast(error.message);
  }
}

async function deleteSelectedEvent() {
  if (!state.editingEvent) {
    return;
  }

  try {
    await api(`/api/events/${state.editingEvent.id}`, { method: "DELETE" });
    closeModal();
    await loadEvents();
    showToast("일정을 삭제했습니다.");
  } catch (error) {
    showToast(error.message);
  }
}

function showToast(message) {
  nodes.toast.textContent = message;
  nodes.toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    nodes.toast.hidden = true;
  }, 2600);
}

function bindEvents() {
  nodes.prevMonth.addEventListener("click", async () => {
    state.currentDate = new Date(state.currentDate.getFullYear(), state.currentDate.getMonth() - 1, 1);
    await loadEvents();
  });

  nodes.nextMonth.addEventListener("click", async () => {
    state.currentDate = new Date(state.currentDate.getFullYear(), state.currentDate.getMonth() + 1, 1);
    await loadEvents();
  });

  nodes.quickAddButton.addEventListener("click", () => {
    const today = new Date();
    const sameMonth = today.getFullYear() === state.currentDate.getFullYear() && today.getMonth() === state.currentDate.getMonth();
    const targetDay = sameMonth ? today.getDate() : 1;
    openAddModal(formatDate(state.currentDate.getFullYear(), state.currentDate.getMonth(), targetDay));
  });

  nodes.closeModal.addEventListener("click", closeModal);
  nodes.eventModal.addEventListener("click", (eventObject) => {
    if (eventObject.target === nodes.eventModal) {
      closeModal();
    }
  });
  nodes.eventForm.addEventListener("submit", saveEvent);
  nodes.deleteButton.addEventListener("click", deleteSelectedEvent);

  document.addEventListener("keydown", (eventObject) => {
    if (eventObject.key === "Escape" && !nodes.eventModal.hidden) {
      closeModal();
    }
  });
}

async function start() {
  bindEvents();
  try {
    state.meta = await api("/api/meta");
    renderMetaControls();
    await loadEvents();
  } catch (error) {
    showToast(error.message);
  }
}

start();
