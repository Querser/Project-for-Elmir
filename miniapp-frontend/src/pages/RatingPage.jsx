import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function RatingPage() {
  const [ratings, setRatings] = useState([]);

  useEffect(() => {
    api.getRatings().then(setRatings);
  }, []);

  return (
    <>
      <h2>Рейтинг игроков</h2>
      {ratings.map((r, i) => (
        <div key={r.id} className="card">
          <b>{i + 1}. {r.player_name}</b>
          <p>Очки: {r.points}</p>
          <p>Уровень: {r.level_name}</p>
        </div>
      ))}
    </>
  );
}
