export interface CronPreset {
  id: string;
  label: string;
  cron: string;
}

export interface CustomCronState {
  minute: string[];
  hour: string[];
  dayOfMonth: string[];
  month: string[];
  dayOfWeek: string[];
}

export type CustomCronField = keyof CustomCronState;

export const defaultCustomCron: CustomCronState = {
  minute: ["*"],
  hour: ["*"],
  dayOfMonth: ["*"],
  month: ["*"],
  dayOfWeek: ["*"],
};

const range = (start: number, end: number) =>
  Array.from({ length: end - start + 1 }, (_, index) => String(start + index));

export const dayOfWeekLabels: Record<string, string> = {
  "0": "Sun",
  "1": "Mon",
  "2": "Tue",
  "3": "Wed",
  "4": "Thu",
  "5": "Fri",
  "6": "Sat",
};

export const monthLabels: Record<string, string> = {
  "1": "Jan",
  "2": "Feb",
  "3": "Mar",
  "4": "Apr",
  "5": "May",
  "6": "Jun",
  "7": "Jul",
  "8": "Aug",
  "9": "Sep",
  "10": "Oct",
  "11": "Nov",
  "12": "Dec",
};

export const customCronOptions: Record<CustomCronField, string[]> = {
  minute: ["*", ...range(0, 59)],
  hour: ["*", ...range(0, 23)],
  dayOfMonth: ["*", ...range(1, 31)],
  month: ["*", ...range(1, 12)],
  dayOfWeek: ["*", ...range(0, 6)],
};

export const compactSelection = (values: string[]) => {
  if (!values.length || values.includes("*")) {
    return "*";
  }
  return values.join(",");
};

export const formatSelection = (values: string[], labelMap?: Record<string, string>) => {
  if (!values.length || values.includes("*")) {
    return "any";
  }
  const labels = labelMap ? values.map((value) => labelMap[value] || value) : values;
  return labels.join(", ");
};

export const formatTime = (hour: string, minute: string) => {
  const hourNum = Number(hour);
  const minuteNum = Number(minute);
  if (Number.isNaN(hourNum) || Number.isNaN(minuteNum)) {
    return `${hour}:${minute}`;
  }
  const suffix = hourNum >= 12 ? "PM" : "AM";
  const hour12 = hourNum % 12 === 0 ? 12 : hourNum % 12;
  return `${hour12}:${String(minuteNum).padStart(2, "0")} ${suffix}`;
};

export const buildCron = (customCron: CustomCronState) =>
  `${compactSelection(customCron.minute)} ${compactSelection(customCron.hour)} ${compactSelection(customCron.dayOfMonth)} ${compactSelection(customCron.month)} ${compactSelection(customCron.dayOfWeek)}`.trim();

export const parseCron = (cron: string): CustomCronState => {
  if (!cron) {
    return { ...defaultCustomCron };
  }
  const parts = cron.trim().split(/\s+/);
  if (parts.length < 5) {
    return { ...defaultCustomCron };
  }
  return {
    minute: (parts[0] || "*").split(","),
    hour: (parts[1] || "*").split(","),
    dayOfMonth: (parts[2] || "*").split(","),
    month: (parts[3] || "*").split(","),
    dayOfWeek: (parts[4] || "*").split(","),
  };
};

export const resolveCronPreset = (cron: string, presets: CronPreset[]) => {
  const preset = presets.find((item) => item.cron === cron);
  return preset ? preset.id : "custom";
};

export const normalizeCronSelection = (values: string[]) => {
  const cleaned = values.includes("*") && values.length > 1
    ? values.filter((item) => item !== "*")
    : values;
  return cleaned.length ? cleaned : ["*"];
};

const joinWithAnd = (values: string[]) => {
  if (values.length <= 1) {
    return values[0] || "";
  }
  if (values.length === 2) {
    return `${values[0]} and ${values[1]}`;
  }
  return `${values.slice(0, -1).join(", ")}, and ${values[values.length - 1]}`;
};

const toOrdinal = (value: string) => {
  const number = Number(value);
  if (Number.isNaN(number)) {
    return value;
  }
  const mod100 = number % 100;
  if (mod100 >= 11 && mod100 <= 13) {
    return `${number}th`;
  }
  switch (number % 10) {
    case 1:
      return `${number}st`;
    case 2:
      return `${number}nd`;
    case 3:
      return `${number}rd`;
    default:
      return `${number}th`;
  }
};

const formatDayOfWeekList = (values: string[]) => {
  const normalized = values.filter((value) => value !== "*");
  if (!normalized.length) {
    return "every day";
  }
  if (normalized.join(",") === "1,2,3,4,5") {
    return "weekdays";
  }
  if (normalized.join(",") === "0,6") {
    return "weekends";
  }
  return joinWithAnd(normalized.map((value) => dayOfWeekLabels[value] || value));
};

const formatMonthList = (values: string[]) => {
  const normalized = values.filter((value) => value !== "*");
  if (!normalized.length) {
    return "every month";
  }
  return joinWithAnd(normalized.map((value) => monthLabels[value] || value));
};

const formatDayOfMonthList = (values: string[]) => {
  const normalized = values.filter((value) => value !== "*");
  if (!normalized.length) {
    return "every day";
  }
  return joinWithAnd(normalized.map((value) => toOrdinal(value)));
};

const getTimeSummary = (customCron: CustomCronState) => {
  const minutes = customCron.minute.filter((value) => value !== "*");
  const hours = customCron.hour.filter((value) => value !== "*");

  if (!minutes.length && !hours.length) {
    return "every minute";
  }
  if (!minutes.length && hours.length) {
    return `every minute during the ${joinWithAnd(hours.map((hour) => formatTime(hour, "00")))} hour`;
  }
  if (minutes.length && !hours.length) {
    if (minutes.length === 1) {
      return `at ${minutes[0]} minutes past every hour`;
    }
    return `at ${joinWithAnd(minutes)} minutes past every hour`;
  }
  if (minutes.length === 1 && hours.length === 1) {
    return `at ${formatTime(hours[0], minutes[0])}`;
  }
  if (minutes.length === 1) {
    return `at ${minutes[0]} minutes past ${joinWithAnd(hours.map((hour) => formatTime(hour, minutes[0])) )}`;
  }
  if (hours.length === 1) {
    return `at ${joinWithAnd(minutes.map((minute) => formatTime(hours[0], minute)))}`;
  }

  const expandedTimes = hours.flatMap((hour) => minutes.map((minute) => formatTime(hour, minute)));
  if (expandedTimes.length <= 8) {
    return `at ${joinWithAnd(expandedTimes)}`;
  }
  return `at ${joinWithAnd(minutes)} minutes past ${joinWithAnd(hours.map((hour) => formatTime(hour, "00")))}`;
};

const getDateSummary = (customCron: CustomCronState) => {
  const months = customCron.month.filter((value) => value !== "*");
  const dayOfMonth = customCron.dayOfMonth.filter((value) => value !== "*");
  const dayOfWeek = customCron.dayOfWeek.filter((value) => value !== "*");

  if (!months.length && !dayOfMonth.length && !dayOfWeek.length) {
    return "every day";
  }
  if (!months.length && !dayOfMonth.length && dayOfWeek.length) {
    return `on ${formatDayOfWeekList(customCron.dayOfWeek)}`;
  }
  if (!months.length && dayOfMonth.length && !dayOfWeek.length) {
    return `on the ${formatDayOfMonthList(customCron.dayOfMonth)} of every month`;
  }
  if (months.length && !dayOfMonth.length && !dayOfWeek.length) {
    return `every day in ${formatMonthList(customCron.month)}`;
  }
  if (months.length && dayOfMonth.length && !dayOfWeek.length) {
    return `on the ${formatDayOfMonthList(customCron.dayOfMonth)} of ${formatMonthList(customCron.month)}`;
  }
  if (months.length && !dayOfMonth.length && dayOfWeek.length) {
    return `on ${formatDayOfWeekList(customCron.dayOfWeek)} in ${formatMonthList(customCron.month)}`;
  }
  if (!months.length && dayOfMonth.length && dayOfWeek.length) {
    return `on matching days each month: the ${formatDayOfMonthList(customCron.dayOfMonth)}, or ${formatDayOfWeekList(customCron.dayOfWeek)}`;
  }
  return `on matching days in ${formatMonthList(customCron.month)}: the ${formatDayOfMonthList(customCron.dayOfMonth)}, or ${formatDayOfWeekList(customCron.dayOfWeek)}`;
};

export const getCronSummary = (cron: string, customCron: CustomCronState, options?: { emptyText?: string; prefix?: string }) => {
  const prefix = options?.prefix || "Runs";
  if (!cron) {
    return options?.emptyText || "No schedule selected yet.";
  }

  const timeSummary = getTimeSummary(customCron);
  const dateSummary = getDateSummary(customCron);

  if (timeSummary === "every minute" && dateSummary === "every day") {
    return `${prefix} every minute.`;
  }

  return `${prefix} ${timeSummary}, ${dateSummary}.`;
};