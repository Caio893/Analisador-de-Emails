export type RiskLevel = "trusted" | "slightly_trusted" | "suspicious" | "dangerous";
export type Folder = "inbox" | "spam";
export type AnalysisStatus = "pending" | "local" | "analyzed";

export interface Email {
  id: string;
  from: string;
  fromEmail: string;
  subject: string;
  preview: string;
  body?: string;
  displayBodyHtml?: string;
  displayBodyText?: string;
  displayBodySource?: "gmail-html" | "gmail-text" | "gmail" | "stored";
  time: string; // ISO
  folder: Folder;
  risk: RiskLevel;
  riskScore: number; // 0-100
  aiReason: string;
  analysisStatus?: AnalysisStatus;
  hasAttachments?: boolean;
  attachmentCount?: number;
  trustedRule?: {
    ruleType: "email" | "domain";
    value: string;
  } | null;
  metadata?: Record<string, unknown>;
  unread?: boolean;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  hasMore: boolean;
}

export interface InboxSummary {
  analyzedToday: number;
  spamDetected: number;
  suspicious: number;
  riskRate: number; // 0-100
}

export interface AnalyzeFolderResult {
  account: string;
  folder: Folder;
  total: number;
  eligible: number;
  skippedAlreadyAnalyzed: number;
  analyzed: number;
  aiAnalyzed: number;
  localFallback: number;
  trusted: number;
  queued?: number;
  failed: number;
  errors: Array<{
    emailId: string;
    detail: string;
  }>;
}
