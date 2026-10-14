/**
 * Application Feature Flags & Configuration
 * 
 * Centralized feature flags for controlling experimental, dev/testing,
 * and deployment-scoped features.
 */

export const FEATURES = {
  /**
   * Enables the real-time AI Proctoring / Live Monitoring Mirror panel
   * for students during exam taking.
   * 
   * Development / Testing only. Set to false in production to completely
   * disable student-side monitoring previews.
   */
  STUDENT_MONITORING_PREVIEW: import.meta.env.VITE_ENABLE_STUDENT_MONITORING_PREVIEW === 'true'
};

/**
 * Helper to check if the student monitoring preview is active.
 */
export const isStudentMonitoringPreviewEnabled = (): boolean => {
  return FEATURES.STUDENT_MONITORING_PREVIEW;
};
