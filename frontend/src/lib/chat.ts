/**
 * Chat API Client — UdyamSetu AI Assistant
 * Frontend library for AI chat conversations, RAG-grounded messaging,
 * and knowledge base operations.
 */

import { apiFetch } from "./auth";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ConversationSummary {
  id: string;
  title: string;
  status: string;
  context_type: string | null;
  total_messages: number;
  total_tokens_used: number;
  last_message_at: string | null;
  created_at: string | null;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sequence_number: number;
  model_used: string | null;
  provider_used: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  sources: SourceCitation[] | null;
  confidence_score: number | null;
  user_rating: number | null;
  created_at: string;
}

export interface SourceCitation {
  index: number;
  document_id: string;
  document_title: string;
  category: string;
  relevance_score: number;
  chunk_preview: string;
}

export interface Conversation {
  id: string;
  title: string;
  status: string;
  context_type: string | null;
  total_messages: number;
  total_tokens_used: number;
  last_message_at: string | null;
  created_at: string | null;
  messages: ConversationMessage[];
}

export interface SendMessageResponse {
  status: string;
  user_message: ConversationMessage;
  assistant_message: ConversationMessage;
  sources: SourceCitation[];
  model: string;
  provider: string;
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  category: string;
  processing_status: string;
  chunk_count: number;
  source_url: string | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Conversation API
// ---------------------------------------------------------------------------

export async function createConversation(
  title = "New Conversation",
  contextType = "general",
  businessId?: string,
): Promise<ConversationSummary> {
  const res = await apiFetch<{ conversation: ConversationSummary }>("/chat/conversations", {
    method: "POST",
    body: JSON.stringify({ title, context_type: contextType, business_id: businessId }),
  });
  return res.conversation;
}

export async function listConversations(
  status = "active",
  limit = 50,
): Promise<ConversationSummary[]> {
  const res = await apiFetch<{ conversations: ConversationSummary[] }>(
    `/chat/conversations?status=${status}&limit=${limit}`,
  );
  return res.conversations;
}

export async function getConversation(conversationId: string): Promise<Conversation> {
  const res = await apiFetch<{ conversation: Conversation }>(
    `/chat/conversations/${conversationId}`,
  );
  return res.conversation;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiFetch(`/chat/conversations/${conversationId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Messaging API
// ---------------------------------------------------------------------------

export async function sendMessage(
  conversationId: string,
  message: string,
  contextType?: string,
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>(
    `/chat/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ message, context_type: contextType }),
    },
  );
}

export async function quickChat(
  message: string,
  contextType?: string,
): Promise<{ response: string; sources: SourceCitation[]; model: string }> {
  return apiFetch(`/chat/quick`, {
    method: "POST",
    body: JSON.stringify({ message, context_type: contextType }),
  });
}

export async function rateMessage(messageId: string, rating: number): Promise<void> {
  await apiFetch(`/chat/messages/${messageId}/rate`, {
    method: "POST",
    body: JSON.stringify({ rating }),
  });
}

// ---------------------------------------------------------------------------
// AI Next Actions
// ---------------------------------------------------------------------------

export async function getNextActions(
  businessId?: string,
): Promise<{ suggestions: string; model: string; provider: string }> {
  const params = businessId ? `?business_id=${businessId}` : "";
  return apiFetch(`/chat/next-actions${params}`);
}

// ---------------------------------------------------------------------------
// Knowledge Base API
// ---------------------------------------------------------------------------

export async function seedKnowledgeBase(): Promise<{ message: string; documents: KnowledgeDocument[] }> {
  return apiFetch("/chat/knowledge/seed", { method: "POST" });
}

export async function listKnowledgeDocuments(
  category?: string,
): Promise<KnowledgeDocument[]> {
  const params = category ? `?category=${category}` : "";
  const res = await apiFetch<{ documents: KnowledgeDocument[] }>(
    `/chat/knowledge/documents${params}`,
  );
  return res.documents;
}

export async function getKnowledgeStats(): Promise<{
  total_documents: number;
  total_chunks: number;
  embedded_chunks: number;
}> {
  return apiFetch("/chat/knowledge/stats");
}
