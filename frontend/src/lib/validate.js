// Soft input validation — warn, don't block (see TODOS: soft-required policy).
// All validators treat EMPTY as valid: requiredness is a separate concern
// handled at the action that needs the field (e.g. email at quote send).

export function isValidEmail(value) {
  const s = (value || "").trim();
  if (!s) return true;
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(s);
}

export function isValidPhone(value) {
  const s = (value || "").trim();
  if (!s) return true;
  const digits = s.replace(/\D/g, "");
  return digits.length === 10 || (digits.length === 11 && digits.startsWith("1"));
}

export function isValidZip(value) {
  const s = (value || "").trim();
  if (!s) return true;
  return /^\d{5}(-\d{4})?$/.test(s);
}

/** Normalize a valid 10-digit US number to "(AAA) BBB-CCCC" on blur.
 *  Anything that isn't cleanly 10 digits (extensions, international,
 *  partial entries) is returned untouched. */
export function formatPhoneUS(value) {
  const s = (value || "").trim();
  let digits = s.replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("1")) digits = digits.slice(1);
  if (digits.length !== 10) return value;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
}
