import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import TrainingCard from "../components/TrainingCard.jsx";

export default function SchedulePage({ onOpenTraining }) {
  const [trainings, setTrainings] = useState([]);

  useEffect(() => {
    api.getTrainings().then((data) => {
      setTrainings(data.items || []);
    });
  }, []);

  return (
    <>
      <h2>Расписание</h2>
      {trainings.map((t) => (
        <TrainingCard key={t.id} training={t} onClick={() => onOpenTraining(t.id)} />
      ))}
    </>
  );
}
