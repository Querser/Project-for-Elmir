import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function NotificationsPage() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    api.getNotifications().then((data) => setItems(data.items || []));
  }, []);

  return (
    <>
      <h2>Уведомления</h2>
      {items.length === 0 && <p>У вас нет уведомлений</p>}
      {items.map((n) => (
        <div key={n.id} className="card">
          <b>{n.title}</b>
          <p>{n.text}</p>
        </div>
      ))}
    </>
  );
}
