import { type Currency } from "@/lib/types/domain";

const currencyFormatters: Record<Currency, Intl.NumberFormat> = {
  USD: new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }),
  EUR: new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }),
  GBP: new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }),
  CHF: new Intl.NumberFormat("de-CH", { style: "currency", currency: "CHF" }),
  VES: new Intl.NumberFormat("es-VE", { style: "currency", currency: "VES" }),
  BRL: new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }),
};

export function formatMoney(value: number, currency: Currency = "USD"): string {
  return (currencyFormatters[currency] ?? currencyFormatters.USD).format(value);
}

export function formatPct(value: number, decimals = 2): string {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(decimals)}%`;
}

export function formatNumber(value: number, decimals = 0): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("es-ES", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(" ");
}
