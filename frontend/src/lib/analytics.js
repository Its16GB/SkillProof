import posthog from "posthog-js";

const POSTHOG_KEY = process.env.REACT_APP_POSTHOG_KEY;
const POSTHOG_HOST =
  process.env.REACT_APP_POSTHOG_HOST || "https://us.i.posthog.com";

export const analyticsEnabled = Boolean(POSTHOG_KEY && POSTHOG_HOST);

if (analyticsEnabled) {
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    autocapture: false,
    capture_pageview: true,
    capture_pageleave: true,
    disable_session_recording: true,
    person_profiles: "identified_only",
  });
}

export const capture = (event, properties = {}) => {
  if (analyticsEnabled) {
    posthog.capture(event, properties);
  }
};

export const experienceBand = (years) => {
  if (years <= 1) return "0-1";
  if (years <= 3) return "2-3";
  if (years <= 6) return "4-6";
  if (years <= 10) return "7-10";
  return "11+";
};
