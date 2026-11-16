const MINUS = "−";
const whole = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
const paise = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function formatINR(amount: number, opts?: { paise?: boolean }): string {
  const value = opts?.paise
    ? Math.round(Math.abs(amount) * 100) / 100
    : Math.round(Math.abs(amount));
  const body = opts?.paise ? paise.format(value) : whole.format(value);
  const sign = amount < 0 && value > 0 ? MINUS : "";
  return `${sign}₹${body}`;
}

export function formatLakh(amount: number): string {
  const abs = Math.abs(amount);
  if (abs < 100000) return formatINR(amount);
  const sign = amount < 0 ? MINUS : "";
  if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} crore`;
  return `${sign}₹${(abs / 100000).toFixed(2)} lakh`;
}
