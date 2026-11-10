export const STATE_LABEL: Record<string, string> = {
  approved: "Verified", declined: "Not verified", review_required: "Needs review", action_required: "Retry requested",
  created: "Sent", in_progress: "In progress", processing: "Processing", expired: "Expired", cancelled: "Cancelled", error: "Provider delay",
};
export const STATE_TONE: Record<string, string> = { approved: "good", declined: "bad", review_required: "warn", action_required: "warn", error: "warn" };
export const CHECK_LABEL: Record<string, string> = {
  government_id: "Government ID", face_match: "Face match", liveness: "Liveness", email: "Email ownership", phone: "Phone ownership",
};
export const RESULT_LABEL: Record<string, string> = { pass: "Passed", fail: "Failed", inconclusive: "Review needed", error: "Provider error", not_run: "Pending" };
export const RESULT_TONE: Record<string, string> = { pass: "good", fail: "bad", inconclusive: "warn", error: "warn" };
export const REASON_TEXT: Record<string, string> = {
  "liveness.inconclusive": "Liveness was inconclusive.", "liveness.suspected_attack": "Possible spoofing was flagged.",
  "liveness.failed": "Liveness did not pass.", "face.no_match": "The selfie did not match the document photo.",
  "capture.low_quality": "Image quality may have affected the result.", "evidence.missing": "A required check is missing.",
  "document.expired": "The document has expired.", "document.authenticity_failed": "Document authenticity did not pass.",
  "document.unsupported": "Unsupported document.", "provider.unavailable": "The provider was unavailable.",
};
export const METHOD_LABEL: Record<string, string> = { automated: "Automated", evidence_review: "Evidence review", alternative_method: "Alternative method" };
