import React from "react";

export default function TrainingCard({ training, onClick }) {
  return (
    <div className="card" onClick={onClick}>
      <b>{training.title || "Тренировка"}</b>
      <p>
        <b>Время:</b> {training.starts_at ? new Date(training.starts_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }) : ""}
      </p>
      <p>
        <b>Место:</b> {training.address || "Не указано"}
      </p>
      <p>
        Осталось {training.free_places ?? "?"} мест
      </p>
    </div>
  );
}
