export type TgWebApp = {
  initData?: string;
  initDataUnsafe?: any;
  ready?: () => void;
  expand?: () => void;
  openLink?: (url: string) => void;
  close?: () => void;
};

export function getTelegram(): TgWebApp | null {
  const tg = (window as any)?.Telegram?.WebApp as TgWebApp | undefined;
  return tg || null;
}

export function getTelegramInitData(): string {
  const tg = getTelegram();
  return tg?.initData || "";
}

export function getTelegramUser(): any | null {
  const tg = getTelegram();
  return tg?.initDataUnsafe?.user || null;
}

export function telegramReadyExpand(): void {
  const tg = getTelegram();
  try {
    tg?.ready?.();
    tg?.expand?.();
  } catch {
    // ignore
  }
}

export function openExternalLink(url: string): void {
  const tg = getTelegram();
  try {
    tg?.openLink?.(url);
  } catch {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}
