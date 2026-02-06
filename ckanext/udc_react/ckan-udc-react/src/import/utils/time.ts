const ISO_TZ_PATTERN = /(Z|[+-]\d{2}:\d{2})$/;

const normalizeIsoTimestamp = (value: string): string => {
  if (!value) {
    return value;
  }
  if (ISO_TZ_PATTERN.test(value)) {
    return value;
  }
  return `${value}Z`;
};

export const formatLocalTimestamp = (value: string | null): string => {
  if (!value) {
    return "never";
  }
  const normalized = normalizeIsoTimestamp(value);
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
};
