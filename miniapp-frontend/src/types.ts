export type FiltersState = {
  type: Set<string>;
  level: Set<string>;
  location: Set<string>; // Этап 12.2: место проведения (адрес + название)
};

export type Training = {
  id: string | number;

  title: string;
  titleFull: string;

  start_at: string | null;
  time: string;
  timeRange: string;

  address: string;          // строка "Москва, ул..."
  locationTitle?: string;   // если есть "Зал №1 / Лужники" и т.п.
  locationDisplay: string;  // то, что показываем в фильтре и карточке

  trainer: string;
  levels: string[];

  capacity: number;
  free: number;
  occupied: number;

  price: number;

  can_enroll: boolean;
  user_enrollment_status: string;

  with_coach: boolean;

  image_url?: string | null;
};

export type LocationOption = {
  key: string;       // уникальный ключ (обычно строка locationDisplay)
  title: string;     // то, что показываем (адрес + название)
};
