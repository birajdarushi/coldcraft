// Presentation constants (labels/ordering). NOT data — these mirror the
// status vocabulary the API emits so the UI can render them consistently.

export const STATUS_LABELS = {
  draft: "DRAFT",
  self_review: "SELF_REVIEW",
  qa_passed: "QA_PASSED",
  user_approved: "USER_APPROVED",
  sent: "SENT",
  opened: "OPENED",
  clicked: "CLICKED",
  replied: "REPLIED",
  blocked: "BLOCKED",
};

export const STATUS_ORDER = [
  "draft",
  "self_review",
  "qa_passed",
  "user_approved",
  "sent",
  "opened",
  "clicked",
  "replied",
  "blocked",
];
