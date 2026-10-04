"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  createConversation,
  listConversations,
  getConversation,
  deleteConversation,
  sendMessage,
  rateMessage,
  ConversationSummary,
  ConversationMessage,
  SourceCitation,
} from "@/lib/chat";

/* ------------------------------------------------------------------ */
/*  Chat Page — UdyamSetu AI Assistant                                */
/* ------------------------------------------------------------------ */

export default function AssistantPage() {
  /* ---- state ---- */
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sendingMsg, setSendingMsg] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [latestSources, setLatestSources] = useState<SourceCitation[]>([]);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  /* ---- helpers ---- */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  /* ---- load conversations ---- */
  const loadConversations = useCallback(async () => {
    try {
      const convs = await listConversations();
      setConversations(convs);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  /* ---- load conversation messages ---- */
  const loadConversation = useCallback(async (convId: string) => {
    setLoading(true);
    try {
      const conv = await getConversation(convId);
      setMessages(conv.messages || []);
      setActiveConvId(convId);
      setLatestSources([]);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  /* ---- new conversation ---- */
  const handleNewConversation = async () => {
    try {
      const conv = await createConversation();
      await loadConversations();
      setActiveConvId(conv.id);
      setMessages([]);
      setLatestSources([]);
      inputRef.current?.focus();
    } catch {
      /* ignore */
    }
  };

  /* ---- delete conversation ---- */
  const handleDeleteConversation = async (convId: string) => {
    try {
      await deleteConversation(convId);
      if (activeConvId === convId) {
        setActiveConvId(null);
        setMessages([]);
      }
      await loadConversations();
    } catch {
      /* ignore */
    }
  };

  /* ---- send message ---- */
  const handleSend = async () => {
    if (!input.trim() || sendingMsg) return;

    let convId = activeConvId;

    /* auto-create conversation on first message */
    if (!convId) {
      try {
        const conv = await createConversation(input.slice(0, 60));
        convId = conv.id;
        setActiveConvId(convId);
        await loadConversations();
      } catch {
        return;
      }
    }

    const userText = input.trim();
    setInput("");
    setSendingMsg(true);

    /* optimistic user bubble */
    const optimisticMsg: ConversationMessage = {
      id: "temp-" + Date.now(),
      conversation_id: convId,
      role: "user",
      content: userText,
      sequence_number: messages.length + 1,
      model_used: null,
      provider_used: null,
      prompt_tokens: 0,
      completion_tokens: 0,
      total_tokens: 0,
      sources: null,
      confidence_score: null,
      user_rating: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    try {
      const res = await sendMessage(convId, userText);
      setMessages((prev) => {
        const withoutOptimistic = prev.filter((m) => m.id !== optimisticMsg.id);
        return [...withoutOptimistic, res.user_message, res.assistant_message];
      });
      setLatestSources(res.sources || []);
      await loadConversations();
    } catch {
      setMessages((prev) => prev.filter((m) => m.id !== optimisticMsg.id));
      setInput(userText);
    } finally {
      setSendingMsg(false);
      inputRef.current?.focus();
    }
  };

  /* ---- rate message ---- */
  const handleRate = async (msgId: string, rating: number) => {
    try {
      await rateMessage(msgId, rating);
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, user_rating: rating } : m))
      );
    } catch {
      /* ignore */
    }
  };

  /* ---- keyboard ---- */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /* ---- quick prompts ---- */
  const quickPrompts = [
    "What approvals do I need to start a food processing unit in Maharashtra?",
    "Explain the PMEGP scheme eligibility criteria",
    "What are the compliance deadlines for GST returns?",
    "How to obtain Consent to Operate from the Pollution Control Board?",
  ];

  /* ================================================================ */
  /*  RENDER                                                          */
  /* ================================================================ */

  return (
    <div className="flex h-[calc(100vh-64px)] bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      {/* ---- SIDEBAR ---- */}
      <aside
        className={`${sidebarOpen ? "w-72" : "w-0"} transition-all duration-300 overflow-hidden border-r border-slate-200 bg-white/80 backdrop-blur-md flex flex-col`}
      >
        {/* header */}
        <div className="p-4 border-b border-slate-100">
          <button
            onClick={handleNewConversation}
            className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-medium text-sm hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
            New Conversation
          </button>
        </div>

        {/* conversation list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 && (
            <p className="text-xs text-slate-400 text-center mt-8 px-4">
              No conversations yet. Start chatting with UdyamSetu AI!
            </p>
          )}
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all text-sm ${
                activeConvId === conv.id
                  ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                  : "hover:bg-slate-50 text-slate-700"
              }`}
              onClick={() => loadConversation(conv.id)}
            >
              <svg className="w-4 h-4 shrink-0 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
              <span className="flex-1 truncate">{conv.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteConversation(conv.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition-all"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* ---- MAIN CHAT AREA ---- */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* top bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 bg-white/60 backdrop-blur-sm">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 transition-all"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-md">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
            </div>
            <div>
              <h1 className="font-semibold text-slate-800 text-sm">UdyamSetu AI Assistant</h1>
              <p className="text-xs text-slate-400">RAG-powered regulatory guidance</p>
            </div>
          </div>
          {latestSources.length > 0 && (
            <button
              onClick={() => setSourcesOpen(!sourcesOpen)}
              className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 text-amber-700 text-xs font-medium hover:bg-amber-100 transition-all border border-amber-200"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              {latestSources.length} Sources
            </button>
          )}
        </div>

        {/* message area */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 && !loading ? (
            /* empty state / quick prompts */
            <div className="flex flex-col items-center justify-center h-full px-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-6 shadow-xl">
                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
              </div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">How can I help you today?</h2>
              <p className="text-sm text-slate-500 mb-8 max-w-md text-center">
                Ask about industrial approvals, government schemes, compliance requirements, or document guidance.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl w-full">
                {quickPrompts.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInput(prompt);
                      inputRef.current?.focus();
                    }}
                    className="text-left p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 text-sm text-slate-600 hover:text-indigo-700 transition-all group"
                  >
                    <span className="text-indigo-500 mr-2 group-hover:text-indigo-600">→</span>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* message bubbles */
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0 mt-1 shadow-md">
                      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                    </div>
                  )}
                  <div
                    className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md"
                        : "bg-white border border-slate-200 text-slate-700 shadow-sm"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.content}</div>

                    {/* sources badge */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-100">
                        <p className="text-xs text-slate-400 mb-1">Sources:</p>
                        <div className="flex flex-wrap gap-1">
                          {msg.sources.map((s: SourceCitation, i: number) => (
                            <span
                              key={i}
                              className="inline-flex items-center px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-600 text-xs font-medium"
                              title={s.chunk_preview}
                            >
                              [{s.index}] {s.document_title}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* rating buttons for assistant messages */}
                    {msg.role === "assistant" && !msg.id.startsWith("temp-") && (
                      <div className="mt-2 flex items-center gap-2">
                        <button
                          onClick={() => handleRate(msg.id, 5)}
                          className={`p-1 rounded transition-all ${
                            msg.user_rating === 5
                              ? "text-green-500"
                              : "text-slate-300 hover:text-green-500"
                          }`}
                          title="Helpful"
                        >
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" /></svg>
                        </button>
                        <button
                          onClick={() => handleRate(msg.id, 1)}
                          className={`p-1 rounded transition-all ${
                            msg.user_rating === 1
                              ? "text-red-500"
                              : "text-slate-300 hover:text-red-500"
                          }`}
                          title="Not helpful"
                        >
                          <svg className="w-4 h-4 rotate-180" fill="currentColor" viewBox="0 0 20 20"><path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" /></svg>
                        </button>
                        {msg.model_used && (
                          <span className="text-xs text-slate-300 ml-auto">{msg.provider_used}:{msg.model_used}</span>
                        )}
                      </div>
                    )}
                  </div>
                  {msg.role === "user" && (
                    <div className="w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center shrink-0 mt-1 shadow-md">
                      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                    </div>
                  )}
                </div>
              ))}

              {/* typing indicator */}
              {sendingMsg && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0 mt-1 shadow-md">
                    <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl px-4 py-3 shadow-sm">
                    <div className="flex gap-1.5">
                      <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* sources panel */}
        {sourcesOpen && latestSources.length > 0 && (
          <div className="border-t border-slate-200 bg-amber-50/50 px-4 py-3 max-h-48 overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-amber-800 uppercase tracking-wide">Source References</h3>
              <button onClick={() => setSourcesOpen(false)} className="text-amber-500 hover:text-amber-700">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="space-y-2">
              {latestSources.map((s, i) => (
                <div key={i} className="bg-white rounded-lg p-3 border border-amber-200 text-xs">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-amber-700">[{s.index}]</span>
                    <span className="font-medium text-slate-700">{s.document_title}</span>
                    <span className="ml-auto px-1.5 py-0.5 rounded bg-amber-100 text-amber-600 font-medium">
                      {(s.relevance_score * 100).toFixed(0)}% relevant
                    </span>
                  </div>
                  <p className="text-slate-500 line-clamp-2">{s.chunk_preview}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* input area */}
        <div className="border-t border-slate-200 bg-white/80 backdrop-blur-sm px-4 py-3">
          <div className="max-w-3xl mx-auto flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about approvals, schemes, compliance..."
                rows={1}
                className="w-full resize-none rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                style={{ maxHeight: "120px" }}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || sendingMsg}
              className="p-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md hover:shadow-lg hover:from-indigo-700 hover:to-purple-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
            </button>
          </div>
          <p className="text-center text-xs text-slate-400 mt-2">
            UdyamSetu AI provides illustrative regulatory guidance. Always verify with official government portals.
          </p>
        </div>
      </div>
    </div>
  );
}
