/**
 * ExamEnvironmentMonitor
 * ======================
 * A pure TypeScript class — no React, no AI engine dependency.
 *
 * Detects deterministic browser signals:
 *   - TAB_SWITCH   → Page Visibility API (visibilityState === "hidden")
 *   - FULLSCREEN_EXIT → Fullscreen API (fullscreenElement === null)
 *
 * Integrates into the existing Violation → Evidence → WebSocket pipeline
 * by calling the /runtime/env-monitor backend endpoints.
 *
 * Rules:
 *  - Only fires violations when isActive === true
 *  - stopMonitoring() sets isActive = false FIRST to prevent false positives on submit
 *  - 250ms debounce correlates simultaneous browser events into ONE violation
 *  - Network failures do not crash the exam — violations are tracked locally and
 *    one retry is attempted; the exam continues regardless
 *  - Does NOT depend on the AI monitoring engine in any way
 */

import apiClient from './apiClient';

export type EnvViolationType = 'TAB_SWITCH' | 'FULLSCREEN_EXIT';

export interface EnvViolationRecord {
  id: number;
  type: EnvViolationType;
  startedAt: Date;
  endedAt?: Date;
  durationSeconds?: number;
  severity: 'HIGH';
  status: 'ACTIVE' | 'PENDING';
}

type ViolationCallback = (v: EnvViolationRecord) => void;

export class ExamEnvironmentMonitor {
  // -----------------------------------------------------------------------
  // State
  // -----------------------------------------------------------------------
  private isActive = false;
  private examId: string | null = null;
  private sessionId: number | null = null;

  // Current open violation (one at a time)
  private currentViolation: EnvViolationRecord | null = null;

  // Event correlation
  private correlationDebounce: ReturnType<typeof setTimeout> | null = null;
  private pendingRawEvents: string[] = [];
  private pendingType: EnvViolationType | null = null;

  // User callbacks
  private onDetectedCb: ViolationCallback | null = null;
  private onResolvedCb: ViolationCallback | null = null;
  private onFullscreenRequiredCb: (() => void) | null = null;
  private snapshotProvider: (() => string | null) | null = null;

  // Bound listener references (needed for removeEventListener)
  private boundVisibility: () => void;
  private boundFullscreen: () => void;

  constructor() {
    this.boundVisibility = this.handleVisibilityChange.bind(this);
    this.boundFullscreen = this.handleFullscreenChange.bind(this);
  }

  // -----------------------------------------------------------------------
  // Public API
  // -----------------------------------------------------------------------

  /**
   * Set a function that extracts a JPEG base64 frame from the candidate's active camera feed.
   */
  setSnapshotProvider(provider: () => string | null): void {
    this.snapshotProvider = provider;
  }

  /**
   * Begin monitoring. Must be called after fullscreen succeeds and the
   * exam session has started.
   */
  startMonitoring(examId: string, sessionId: number): void {
    this.examId = examId;
    this.sessionId = sessionId;
    this.isActive = true;

    document.addEventListener('visibilitychange', this.boundVisibility);
    document.addEventListener('fullscreenchange', this.boundFullscreen);

    console.info('[ExamEnvironmentMonitor] Monitoring STARTED', { examId, sessionId });
  }

  /**
   * Stop monitoring. Call this BEFORE submitting the exam to prevent
   * false violations from the normal fullscreen exit on submission.
   *
   * Idempotent — safe to call multiple times.
   */
  stopMonitoring(): void {
    if (!this.isActive && !this.currentViolation) return;

    // CRITICAL: disable FIRST before removing listeners and resolving open violations
    this.isActive = false;

    // Clear pending correlation debounce immediately
    if (this.correlationDebounce !== null) {
      clearTimeout(this.correlationDebounce);
      this.correlationDebounce = null;
      this.pendingRawEvents = [];
      this.pendingType = null;
    }

    // Remove listeners
    document.removeEventListener('visibilitychange', this.boundVisibility);
    document.removeEventListener('fullscreenchange', this.boundFullscreen);

    // Resolve any open violation that was still ACTIVE when monitoring stopped
    if (this.currentViolation && this.currentViolation.status === 'ACTIVE') {
      const endedAt = new Date();
      const durationSeconds =
        (endedAt.getTime() - this.currentViolation.startedAt.getTime()) / 1000;
      void this.reportViolationEnd(durationSeconds);
    }

    console.info('[ExamEnvironmentMonitor] Monitoring STOPPED');
  }

  /**
   * Register callback to be called when a new violation starts.
   */
  onViolationDetected(cb: ViolationCallback): void {
    this.onDetectedCb = cb;
  }

  /**
   * Register callback to be called when the current violation ends.
   */
  onViolationResolved(cb: ViolationCallback): void {
    this.onResolvedCb = cb;
  }

  /**
   * Register callback when the student returns to page but is missing fullscreen.
   */
  onFullscreenRequired(cb: () => void): void {
    this.onFullscreenRequiredCb = cb;
  }

  /**
   * Public method to finalize open incident once fullscreen is successfully restored by user.
   */
  resolveIncidentIfEnvironmentRestored(): void {
    if (this.currentViolation && this.currentViolation.status === 'ACTIVE') {
      if (document.visibilityState === 'visible' && document.fullscreenElement !== null) {
        this.resolveCurrentViolation();
      }
    }
  }

  // -----------------------------------------------------------------------
  // Private: Browser event handlers
  // -----------------------------------------------------------------------

  private handleVisibilityChange(): void {
    if (!this.isActive) return;

    if (document.visibilityState === 'hidden') {
      // Page became hidden — student left the exam environment
      this.correlateAndFire('visibilitychange:hidden', 'TAB_SWITCH');
    } else if (document.visibilityState === 'visible') {
      // Student returned to tab. Check if fullscreen is still active.
      if (document.fullscreenElement === null) {
        // Fullscreen was dropped while away — notify UI to show blocking recovery screen
        if (this.onFullscreenRequiredCb) {
          this.onFullscreenRequiredCb();
        }
        // Do NOT resolve violation yet — incident remains active until fullscreen restored!
      } else {
        // Fullscreen is still intact — resolve violation
        this.resolveCurrentViolation();
      }
    }
  }

  private handleFullscreenChange(): void {
    if (!this.isActive) return;

    if (document.fullscreenElement === null) {
      // Fullscreen was exited — student left the controlled environment
      // If violation is already active, do not create duplicate violation
      if (!this.currentViolation || this.currentViolation.status !== 'ACTIVE') {
        if (document.visibilityState === 'visible') {
          this.correlateAndFire('fullscreenchange:exited', 'FULLSCREEN_EXIT');
        } else {
          this.pendingRawEvents.push('fullscreenchange:exited');
        }
      }
      // Notify UI that fullscreen recovery is required
      if (this.onFullscreenRequiredCb) {
        this.onFullscreenRequiredCb();
      }
    } else {
      // Fullscreen restored — check if page is visible to resolve active incident
      if (document.visibilityState === 'visible') {
        this.resolveCurrentViolation();
      }
    }
  }

  // -----------------------------------------------------------------------
  // Private: Event correlation (250ms debounce = one incident per action)
  // -----------------------------------------------------------------------

  private correlateAndFire(rawEvent: string, type: EnvViolationType): void {
    // Accumulate raw events within the debounce window
    this.pendingRawEvents.push(rawEvent);

    // If no pending violation type, set it; otherwise keep first type (primary)
    if (this.pendingType === null) {
      this.pendingType = type;
    }

    // If a violation is already active, just accumulate events (don't double-fire)
    if (this.currentViolation && this.currentViolation.status === 'ACTIVE') {
      return;
    }

    // Reset debounce
    if (this.correlationDebounce !== null) {
      clearTimeout(this.correlationDebounce);
    }

    this.correlationDebounce = setTimeout(() => {
      const fireType = this.pendingType!;
      const rawEvents = [...this.pendingRawEvents];
      this.pendingRawEvents = [];
      this.pendingType = null;
      this.correlationDebounce = null;

      // Final guard: still active and not already in a violation
      if (!this.isActive) return;
      if (this.currentViolation && this.currentViolation.status === 'ACTIVE') return;

      void this.reportViolationStart(fireType, rawEvents);
    }, 250);
  }

  // -----------------------------------------------------------------------
  // Private: Resolve current violation (student returned & fullscreen active)
  // -----------------------------------------------------------------------

  private resolveCurrentViolation(): void {
    if (!this.currentViolation || this.currentViolation.status !== 'ACTIVE') return;

    const endedAt = new Date();
    const durationSeconds =
      (endedAt.getTime() - this.currentViolation.startedAt.getTime()) / 1000;

    void this.reportViolationEnd(durationSeconds);
  }

  // -----------------------------------------------------------------------
  // Private: Backend communication
  // -----------------------------------------------------------------------

  private async reportViolationStart(
    type: EnvViolationType,
    rawEvents: string[]
  ): Promise<void> {
    const startedAt = new Date();

    // Capture visual snapshot from camera feed if available
    let snapshotBase64: string | null = null;
    if (this.snapshotProvider) {
      try {
        snapshotBase64 = this.snapshotProvider();
      } catch (e) {
        console.warn('[ExamEnvironmentMonitor] Snapshot capture warning:', e);
      }
    }

    // Optimistic local record (shown in UI immediately, before server responds)
    const optimisticRecord: EnvViolationRecord = {
      id: -1,          // placeholder until server assigns real ID
      type,
      startedAt,
      severity: 'HIGH',
      status: 'ACTIVE',
    };
    this.currentViolation = optimisticRecord;

    // Notify UI immediately (show snackbar warning)
    if (this.onDetectedCb) {
      this.onDetectedCb({ ...optimisticRecord });
    }

    // Report to backend (with one retry on failure)
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const res = await apiClient.post('/runtime/env-monitor/violation-start', {
          exam_id: parseInt(this.examId || '0'),
          event_type: type,
          raw_browser_events: rawEvents,
          image_base64: snapshotBase64,
        });
        // Update local record with the real server-assigned violation ID
        if (this.currentViolation) {
          this.currentViolation.id = res.data.violation_id;
        }
        console.info('[ExamEnvironmentMonitor] Violation recorded on server:', res.data);
        return;
      } catch (err) {
        console.warn(`[ExamEnvironmentMonitor] violation-start failed (attempt ${attempt + 1}):`, err);
        if (attempt === 0) {
          await new Promise(r => setTimeout(r, 2000)); // wait 2s before retry
        }
      }
    }
    // If both attempts failed, the violation is still tracked locally.
    // The exam continues and the student still sees the warning.
    console.error('[ExamEnvironmentMonitor] Could not persist violation to server after retry. Tracking locally only.');
  }

  private async reportViolationEnd(durationSeconds: number): Promise<void> {
    const violation = this.currentViolation;
    if (!violation) return;

    const endedAt = new Date();

    // Update local state immediately
    violation.status = 'PENDING';
    violation.endedAt = endedAt;
    violation.durationSeconds = durationSeconds;
    this.currentViolation = null;

    // Notify UI (show "violation recorded" warning)
    if (this.onResolvedCb) {
      this.onResolvedCb({ ...violation });
    }

    // Only call backend if we have a real server violation ID
    if (violation.id <= 0) {
      console.warn('[ExamEnvironmentMonitor] Violation has no server ID — skipping violation-end call.');
      return;
    }

    try {
      await apiClient.post('/runtime/env-monitor/violation-end', {
        exam_id: parseInt(this.examId || '0'),
        violation_id: violation.id,
        duration_seconds: durationSeconds,
      });
      console.info('[ExamEnvironmentMonitor] Violation resolved on server:', {
        id: violation.id,
        durationSeconds,
      });
    } catch (err) {
      // Non-fatal — the server can compute duration from created_at vs resolved_at
      console.warn('[ExamEnvironmentMonitor] violation-end call failed (non-fatal):', err);
    }
  }
}
