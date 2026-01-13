import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function TrainingPage({ trainingId, onBack }) {
  const [training, setTraining] = useState(null);

  useEffect(() => {
    if (trainingId) {
      api.getTraining(trainingId).then(setTraining);
    }
  }, [trainingId]);

  if (!training) return <p>Загрузка...</p>;

  return (
    <div>
      <button onClick={onBack}>← Назад</button>
      <h2>{training.title}</h2>
      <p><b>Тренер:</b> {training.coach_name || "Не указан"}</p>
      <p><b>Дата:</b> {new Date(training.start_at).toLocaleDateString("ru-RU")}</p>
      <p><b>Время:</b> {new Date(training.start_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}</p>
      <p><b>Адрес:</b> {training.address}</p>

      <button className="primary-btn" onClick={() => alert("Функция оплаты будет добавлена позже!")}>
        Оплатить
      </button>
    </div>
  );
}
